#!/usr/bin/env python3
"""Stickdatei (SVG) fuer den Applikations-Pinguin aus beispiele/pinguin.jpg.

Stil: Applikation – die Stoffflaechen (Koerper, Gesicht, Bauch, Halstuch,
Fuesse) werden nicht ausgestickt, nur ihre Raender mit Satinstich.
Schnabel und Augen bekommen Fuellstich, die Augenbrauen eine schmale Raupe.

Benoetigt: pillow, numpy, scipy, opencv-python-headless
"""

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import stiche
from bild_zu_stick import fill_region, merge_close_blocks, order_blocks, to_svg

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
# Stiche erzeugen
# ---------------------------------------------------------------------------

class Muster:
    def __init__(self, mm_per_px, ursprung):
        self.mm = mm_per_px
        self.ursprung = np.asarray(ursprung, dtype=float)
        self.ebenen = []  # (farbe, [pfade])

    def px_zu_mm(self, pts):
        return (np.asarray(pts, dtype=float) - self.ursprung) * self.mm

    def add(self, farbe, pfade):
        pfade = [stiche.lock(p) for p in pfade if len(p) > 1]
        if self.ebenen and self.ebenen[-1][0] == farbe:
            self.ebenen[-1][1].extend(pfade)
        else:
            self.ebenen.append((farbe, pfade))

    # -- Satinrand einer Flaeche, verdeckte Abschnitte werden ausgelassen --
    def rand(self, maske, breite, verdeckt=None):
        konturen, _ = cv2.findContours(maske.astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)
        pfade = []
        for k in konturen:
            pts = stiche.resample(self.px_zu_mm(k[:, 0, :]), 0.3, closed=True)
            pts = stiche.smooth(pts, 7, closed=True)
            if verdeckt is None:
                pfade.append(stiche.satin(pts, breite, closed=True))
                continue
            px = np.round(pts / self.mm + self.ursprung).astype(int)
            px[:, 0] = px[:, 0].clip(0, verdeckt.shape[1] - 1)
            px[:, 1] = px[:, 1].clip(0, verdeckt.shape[0] - 1)
            frei = ~verdeckt[px[:, 1], px[:, 0]]
            if frei.all():
                pfade.append(stiche.satin(pts, breite, closed=True))
                continue
            # so drehen, dass die Kontur an einem verdeckten Punkt beginnt
            start = int(np.argmin(frei))
            pts, frei = np.roll(pts, -start, 0), np.roll(frei, -start)
            kanten = np.flatnonzero(np.diff(np.append(frei, False).astype(int)))
            for a, b in zip(kanten[::2] + 1, kanten[1::2] + 1):
                stueck = pts[a:b]
                if len(stueck) * 0.3 >= 2.0:
                    pfade.append(stiche.satin(stueck, breite))
        return pfade

    # -- Naht entlang einer von Hand gesetzten Linie --
    def naht(self, punkte_px, breite):
        pts = stiche.resample(self.px_zu_mm(punkte_px), 0.3)
        return stiche.satin(stiche.smooth(pts, 7), breite)

    # -- Fuellstich (Tatami) --
    def fuellung(self, maske, einzug_mm=0.3):
        r = max(1, round(einzug_mm / self.mm))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        maske = cv2.erode(maske.astype(np.uint8), k).astype(bool)
        bloecke = fill_region(maske, 0.4 / self.mm, 3.0 / self.mm, 0.6 / self.mm)
        bloecke = merge_close_blocks(order_blocks(bloecke), 1.0 / self.mm)
        return [self.px_zu_mm(b) for b in bloecke if len(b) > 1]

    # -- schmale Raupe ueber einen duennen, eher waagrechten Strich --
    def strich(self, maske):
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
        return stiche.satin(self.px_zu_mm(mitte), breite)


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
    muster.add(GRAU, muster.rand(m["koerper"], 2.0,
                                 deckel(m["halstuch"], fuesse)))
    muster.add(GRAU, [muster.naht(NAEHTE["fluegel_links"], 1.6),
                      muster.naht(NAEHTE["fluegel_rechts"], 1.6)])

    muster.add(CREME, muster.rand(m["bauch"], 1.8, deckel(m["halstuch"], fuesse)))
    for teil in m["gesicht"]:
        muster.add(CREME, muster.rand(teil, 1.8,
                                      deckel(m["halstuch"], m["schnabel"])))

    muster.add(BLAU, muster.rand(m["halstuch"], 1.8))
    muster.add(BLAU, [muster.naht(NAEHTE["knoten"], 1.4)])

    for fuss in m["fuesse"]:
        muster.add(ORANGE, muster.rand(fuss, 2.0))
    muster.add(ORANGE, [muster.naht(NAEHTE[n], 1.2) for n in
                        ("zehe_links_1", "zehe_links_2",
                         "zehe_rechts_1", "zehe_rechts_2")])
    muster.add(ORANGE, muster.fuellung(m["schnabel"]))
    muster.add(ORANGE, muster.rand(m["schnabel"], 1.4))

    for auge, licht in zip(m["augen"], m["lichter"]):
        muster.add(SCHWARZ, muster.fuellung(auge & ~licht))
        muster.add(SCHWARZ, muster.rand(auge, 1.0))
    for braue in m["brauen"]:
        muster.add(SCHWARZ, [muster.strich(braue)])

    for licht in m["lichter"]:
        muster.add(WEISS, muster.fuellung(licht, einzug_mm=0.0))

    return muster, breite, hoehe


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def vorschau(muster, breite, hoehe, path, px_per_mm=12):
    """Zeichnet die Stiche als Faeden auf Stoff (PNG)."""
    img = Image.new("RGB", (round(breite * px_per_mm), round(hoehe * px_per_mm)),
                    (244, 241, 234))
    d = ImageDraw.Draw(img)
    faden = max(1, round(0.3 * px_per_mm))
    for farbe, pfade in muster.ebenen:
        for p in pfade:
            d.line([tuple(q * px_per_mm) for q in p], fill=farbe, width=faden,
                   joint="curve")
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
    ebenen = [(f, [[tuple(q) for q in pf] for pf in pfade])
              for f, pfade in muster.ebenen]
    out = Path(args.ausgabe)
    out.write_text(to_svg(ebenen, breite, hoehe, 0.3))
    vorschau(muster, breite, hoehe, out.with_suffix(".png"))

    stiche_ges = sum(len(pf) for _, pfade in muster.ebenen for pf in pfade)
    print(f"Gespeichert: {out} (+ Vorschau {out.with_suffix('.png').name})")
    print(f"Groesse:     {breite:.1f} x {hoehe:.1f} mm")
    print(f"Stiche:      {stiche_ges}")
    print(f"Farbwechsel: {len(muster.ebenen) - 1}")
    for f, pfade in muster.ebenen:
        print(f"  #{f[0]:02x}{f[1]:02x}{f[2]:02x}: "
              f"{sum(len(pf) for pf in pfade)} Stiche, {len(pfade)} Pfade")


if __name__ == "__main__":
    main()
