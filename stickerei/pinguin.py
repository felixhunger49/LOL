#!/usr/bin/env python3
"""Stickdatei (SVG fuer Inkscape/Ink/Stitch) fuer den Applikations-Pinguin.

Stil: Applikation – die Stoffflaechen (Koerper, Gesicht, Bauch, Halstuch,
Fuesse) werden nicht ausgestickt, ihre Raender werden Satinsaeulen.
Schnabel und Augen sind Fuellflaechen, die Augenbrauen schmale Satinsaeulen.
Die Stiche selbst berechnet Ink/Stitch beim Export.

Benoetigt: pillow, numpy, scipy, opencv-python-headless
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import stiche
from inkstitch import Fuellung, Satin, dokument, konturen

HIER = Path(__file__).parent

# Garnfarben
GRAU = (95, 89, 84)
CREME = (232, 222, 204)
BLAU = (98, 128, 148)
ORANGE = (214, 136, 66)
SCHWARZ = (40, 37, 35)
WEISS = (250, 250, 248)

# Naehte ohne eigene Farbflaeche, von Hand im Originalbild (Pixel) abgelesen
NAEHTE = {
    "fluegel_links": [(427, 838), (425, 870), (417, 900), (402, 930),
                      (385, 955), (365, 972), (346, 984)],
    "fluegel_rechts": [(770, 837), (780, 870), (792, 905), (810, 930),
                       (835, 957), (853, 975), (858, 986)],
    "knoten": [(811, 714), (805, 735), (811, 752), (822, 765), (836, 776)],
    "zehe_links_1": [(390, 1114), (397, 1130), (410, 1150)],
    "zehe_links_2": [(440, 1098), (445, 1128), (455, 1153)],
    "zehe_rechts_1": [(810, 1114), (803, 1130), (790, 1150)],
    "zehe_rechts_2": [(760, 1098), (755, 1128), (745, 1153)],
}


# ---------------------------------------------------------------------------
# Bild zerlegen
# ---------------------------------------------------------------------------

def segmentieren(path):
    """Liefert die Masken der einzelnen Stoffteile (Originalaufloesung)."""
    rgb = cv2.medianBlur(np.asarray(Image.open(path).convert("RGB")), 7).astype(int)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (r + g + b) / 3

    hell = lum > 165
    orange = (r - b > 60) & (lum < 200)
    blau = (b - r > 8) & ~orange
    schwarz = lum < 55
    hell &= ~orange & ~blau

    # Hintergrund = helle Flaeche, die den Bildrand beruehrt
    lab, _ = ndimage.label(hell)
    rand = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])
    hintergrund = np.isin(lab, np.unique(rand[rand > 0]))

    def teile(maske, min_px):
        lab, n = ndimage.label(maske)
        groesse = ndimage.sum(maske, lab, range(1, n + 1))
        return [lab == i + 1 for i in np.argsort(-groesse) if groesse[i] >= min_px]

    def glatt(maske, r=3):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        m = cv2.morphologyEx(maske.astype(np.uint8), cv2.MORPH_OPEN, k)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
        return ndimage.binary_fill_holes(m)

    m = {}
    m["koerper"] = glatt(teile(~hintergrund, 1000)[0], 5)

    # Bauch = unterste cremefarbene Flaeche, der Rest gehoert zum Gesicht
    creme = teile(hell & ~hintergrund, 5000)
    creme.sort(key=lambda t: np.argwhere(t)[:, 0].mean())
    m["bauch"] = glatt(creme.pop(), 4)
    m["gesicht"] = [glatt(t, 4) for t in creme]

    m["halstuch"] = glatt(teile(blau, 5000)[0], 4)

    orange_teile = teile(orange, 1500)
    fuesse = [t for t in orange_teile if np.argwhere(t)[:, 0].mean() > 900]
    m["fuesse"] = [glatt(t, 4) for t in fuesse[:2]]
    m["schnabel"] = glatt(next(t for t in orange_teile
                               if np.argwhere(t)[:, 0].mean() < 900), 3)

    # Augen: grosse dunkle Flecken (konvexe Huelle), Brauen: kleine Boegen
    schwarz_teile = teile(schwarz, 150)
    augen, brauen = [], []
    for t in schwarz_teile:
        ys, xs = np.nonzero(t)
        if t.sum() > 2000:
            hull = cv2.convexHull(np.column_stack([xs, ys]).astype(np.int32))
            auge = np.zeros(t.shape, np.uint8)
            cv2.fillPoly(auge, [hull], 1)
            augen.append(auge.astype(bool))
        elif ys.max() < np.argwhere(m["schnabel"])[:, 0].min():
            brauen.append(glatt(t, 1))
    m["augen"] = augen
    m["brauen"] = brauen
    m["lichter"] = [glatt(a & (lum > 200), 1) for a in augen]
    return m


# ---------------------------------------------------------------------------
# Ink/Stitch-Objekte erzeugen
# ---------------------------------------------------------------------------

class Muster:
    def __init__(self, mm_per_px, ursprung):
        self.mm = mm_per_px
        self.ursprung = np.asarray(ursprung, dtype=float)
        self.ebenen = []  # (name, farbe, [objekte])

    def px_zu_mm(self, pts):
        return (np.asarray(pts, dtype=float) - self.ursprung) * self.mm

    def add(self, name, farbe, objekte):
        """Haengt Objekte an; gleiche Farbe hintereinander = gleiche Ebene."""
        if self.ebenen and self.ebenen[-1][1] == farbe:
            self.ebenen[-1][2].extend(objekte)
        else:
            self.ebenen.append((name, farbe, list(objekte)))

    # -- Satinrand einer Flaeche, verdeckte Abschnitte werden ausgelassen --
    def rand(self, maske, farbe, breite, verdeckt=None):
        ks, _ = cv2.findContours(maske.astype(np.uint8), cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_NONE)
        objekte = []
        for k in ks:
            pts = stiche.resample(self.px_zu_mm(k[:, 0, :]), 0.3, closed=True)
            pts = stiche.smooth(pts, 9, closed=True)
            frei = np.ones(len(pts), bool)
            if verdeckt is not None:
                px = np.round(pts / self.mm + self.ursprung).astype(int)
                px[:, 0] = px[:, 0].clip(0, verdeckt.shape[1] - 1)
                px[:, 1] = px[:, 1].clip(0, verdeckt.shape[0] - 1)
                frei = ~verdeckt[px[:, 1], px[:, 0]]
            if frei.all():
                objekte.append(Satin(farbe, pts, breite, geschlossen=True))
                continue
            # so drehen, dass die Kontur an einem verdeckten Punkt beginnt
            start = int(np.argmin(frei))
            pts, frei = np.roll(pts, -start, 0), np.roll(frei, -start)
            kanten = np.flatnonzero(np.diff(np.append(frei, False).astype(int)))
            for a, b in zip(kanten[::2] + 1, kanten[1::2] + 1):
                if (b - a) * 0.3 >= 2.0:
                    objekte.append(Satin(farbe, pts[a:b], breite))
        return objekte

    # -- Naht entlang einer von Hand gesetzten Linie --
    def naht(self, farbe, punkte_px, breite):
        pts = stiche.resample(self.px_zu_mm(punkte_px), 0.3)
        return Satin(farbe, stiche.smooth(pts, 7), breite)

    # -- Fuellflaeche, etwas eingezogen, damit der Satinrand sie abdeckt --
    def fuellung(self, maske, farbe, einzug_mm=0.3, winkel=None):
        r = round(einzug_mm / self.mm)
        if r > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
            maske = cv2.erode(maske.astype(np.uint8), k)
        params = {"angle": winkel} if winkel is not None else None
        return Fuellung(farbe, konturen(maske, self.mm, self.ursprung,
                                        min_flaeche_mm2=0.2), params)

    # -- schmale Satinsaeule ueber einen duennen, eher waagrechten Strich --
    def strich(self, maske, farbe):
        ys, xs = np.nonzero(maske)
        mitte, breite = [], []
        for x in range(xs.min() + 1, xs.max()):
            spalte = ys[xs == x]
            if len(spalte):
                mitte.append((x, spalte.mean()))
                breite.append(len(spalte) * self.mm)
        mitte = stiche.smooth(np.array(mitte, float), 9)
        breite = np.convolve(np.pad(breite, 4, mode="edge"),
                             np.ones(9) / 9, mode="valid")
        breite = np.clip(breite + 0.2, 0.6, 2.5)
        return Satin(farbe, self.px_zu_mm(mitte), breite, sprossenabstand=4)


def erzeugen(bild, hoehe_mm, rand_mm):
    m = segmentieren(bild)
    ys, xs = np.nonzero(m["koerper"])
    mm_per_px = hoehe_mm / (ys.max() - ys.min())
    rand_px = rand_mm / mm_per_px
    muster = Muster(mm_per_px, (xs.min() - rand_px, ys.min() - rand_px))
    breite = (xs.max() - xs.min() + 2 * rand_px) * mm_per_px
    hoehe = (ys.max() - ys.min() + 2 * rand_px) * mm_per_px

    def deckel(*masken, r_mm=0.8):
        """Vereinigung der Masken, etwas vergroessert."""
        alle = np.zeros_like(m["koerper"])
        for mk in masken:
            alle |= mk
        r = max(1, round(r_mm / mm_per_px))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        return cv2.dilate(alle.astype(np.uint8), k).astype(bool)

    fuesse = m["fuesse"][0] | m["fuesse"][1]

    # Reihenfolge = Stickreihenfolge, von unten nach oben
    muster.add("Grau - Koerperrand", GRAU,
               muster.rand(m["koerper"], GRAU, 2.0, deckel(m["halstuch"], fuesse)))
    muster.add("", GRAU, [muster.naht(GRAU, NAEHTE["fluegel_links"], 1.6),
                          muster.naht(GRAU, NAEHTE["fluegel_rechts"], 1.6)])

    muster.add("Creme - Bauch und Gesicht", CREME,
               muster.rand(m["bauch"], CREME, 1.8, deckel(m["halstuch"], fuesse)))
    for teil in m["gesicht"]:
        muster.add("", CREME, muster.rand(teil, CREME, 1.8,
                                          deckel(m["halstuch"], m["schnabel"])))

    muster.add("Blau - Halstuch", BLAU, muster.rand(m["halstuch"], BLAU, 1.8))
    muster.add("", BLAU, [muster.naht(BLAU, NAEHTE["knoten"], 1.4)])

    for fuss in m["fuesse"]:
        muster.add("Orange - Fuesse und Schnabel", ORANGE,
                   muster.rand(fuss, ORANGE, 2.0))
    muster.add("", ORANGE, [muster.naht(ORANGE, NAEHTE[n], 1.2) for n in
                            ("zehe_links_1", "zehe_links_2",
                             "zehe_rechts_1", "zehe_rechts_2")])
    muster.add("", ORANGE, [muster.fuellung(m["schnabel"], ORANGE, winkel=45)])
    muster.add("", ORANGE, muster.rand(m["schnabel"], ORANGE, 1.4))

    for auge, licht in zip(m["augen"], m["lichter"]):
        muster.add("Schwarz - Augen und Brauen", SCHWARZ,
                   [muster.fuellung(auge & ~licht, SCHWARZ, winkel=45)])
        muster.add("", SCHWARZ, muster.rand(auge, SCHWARZ, 1.0))
    for braue in m["brauen"]:
        muster.add("", SCHWARZ, [muster.strich(braue, SCHWARZ)])

    muster.add("Weiss - Lichtpunkte", WEISS,
               [muster.fuellung(licht, WEISS, einzug_mm=0) for licht in m["lichter"]])

    return muster, breite, hoehe


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def vorschau(muster, breite, hoehe, path, px_per_mm=12):
    """Zeichnet die Objekte so, wie sie gestickt werden (ohne Einzelstiche)."""
    img = Image.new("RGB", (round(breite * px_per_mm), round(hoehe * px_per_mm)),
                    (244, 241, 234))
    d = ImageDraw.Draw(img)
    for _, farbe, objekte in muster.ebenen:
        for obj in objekte:
            if isinstance(obj, Satin):
                band = np.vstack([obj.links, obj.rechts[::-1]]) * px_per_mm
                d.polygon([tuple(q) for q in band], fill=farbe)
            else:
                for i, k in enumerate(obj.konturen):
                    d.polygon([tuple(q * px_per_mm) for q in k],
                              fill=farbe if i == 0 else (244, 241, 234))
    img.save(path)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("bild", nargs="?", default=HIER / "beispiele" / "pinguin.jpg")
    p.add_argument("-o", "--ausgabe", default=HIER / "beispiele" / "pinguin.svg")
    p.add_argument("--hoehe", type=float, default=100,
                   help="Hoehe des Motivs in mm (Standard: 100)")
    p.add_argument("--rand", type=float, default=2,
                   help="Freier Rand um das Motiv in mm (Standard: 2)")
    args = p.parse_args(argv)

    muster, breite, hoehe = erzeugen(args.bild, args.hoehe, args.rand)
    out = Path(args.ausgabe)
    out.write_text(dokument([(name, obj) for name, _, obj in muster.ebenen],
                            breite, hoehe))
    vorschau(muster, breite, hoehe, out.with_suffix(".png"))

    print(f"Gespeichert: {out} (+ Vorschau {out.with_suffix('.png').name})")
    print(f"Groesse:     {breite:.1f} x {hoehe:.1f} mm")
    for name, _, objekte in muster.ebenen:
        satins = sum(isinstance(o, Satin) for o in objekte)
        print(f"  {name}: {satins} Satinsaeulen, {len(objekte) - satins} Fuellungen")


if __name__ == "__main__":
    main()
