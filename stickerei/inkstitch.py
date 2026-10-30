"""SVG-Ausgabe mit Ink/Stitch-Objekten.

Statt fertiger Einzelstiche werden Objekte geschrieben, aus denen Ink/Stitch
beim Export die Stiche selbst berechnet:

- Satinsaeule: Pfad mit zwei Schienen (Rails) und Querstreben (Rungs),
  ohne Fuellung, mit inkstitch:satin_column="True"
- Fuellung:    geschlossener Pfad mit Fuellfarbe und ohne Kontur
               (Ink/Stitch stickt ihn als Tatami-Fuellstich)

Die Reihenfolge im Dokument ist die Stickreihenfolge; jede Garnfarbe bekommt
eine eigene Inkscape-Ebene.
"""

import cv2
import numpy as np

import stiche

# Ink/Stitch-Parameter (Namen wie im Ink/Stitch-Parameterdialog)
SATIN_PARAMS = {
    "center_walk_underlay": "True",
    "zigzag_spacing_mm": "0.4",
}
FUELL_PARAMS = {
    "fill_method": "tatami_fill",
    "fill_underlay": "True",
}


class Satin:
    """Satinsaeule entlang einer Mittellinie (Punkte in mm)."""

    def __init__(self, farbe, mitte, breite, geschlossen=False,
                 knotenabstand=0.8, sprossenabstand=8.0, params=None):
        self.farbe = farbe
        self.params = {**SATIN_PARAMS, **(params or {})}
        mitte = np.asarray(mitte, dtype=float)
        c = stiche.resample(mitte, knotenabstand, geschlossen)
        n = stiche.normals(c, geschlossen)
        w = _breiten(mitte, c, breite)
        if geschlossen:
            # Ring an einer Stelle aufbrechen: Schienen enden dort, wo sie beginnen
            c, n, w = (np.vstack([c, c[:1]]), np.vstack([n, n[:1]]),
                       np.append(w, w[0]))
        self.links = c + n * _halbbreite(c, n, w / 2)[:, None]
        self.rechts = c - n * _halbbreite(c, -n, w / 2)[:, None]

        # Querstreben: mindestens 3 (zwei waeren fuer Ink/Stitch mehrdeutig),
        # nie am Anfang oder Ende der Schienen
        laenge = np.linalg.norm(np.diff(c, axis=0), axis=1).sum()
        anzahl = max(3, int(round(laenge / sprossenabstand)))
        idx = np.unique(np.linspace(0, len(c) - 1, anzahl + 2)[1:-1].round().astype(int))
        ueber = (w[idx] / 2 + 0.3)[:, None]
        self.sprossen = [np.array([a, b]) for a, b in
                         zip(c[idx] + n[idx] * ueber, c[idx] - n[idx] * ueber)]

    def d(self):
        return " ".join(_teilpfad(p) for p in [self.links, self.rechts, *self.sprossen])

    def svg(self, id_):
        return (f'<path id="{id_}" d="{self.d()}" '
                f'style="fill:none;stroke:{_hex(self.farbe)};stroke-width:0.2" '
                f'inkstitch:satin_column="True" {_attribute(self.params)}/>')


class Fuellung:
    """Fuellflaeche aus geschlossenen Konturen (aussen + Loecher), in mm."""

    def __init__(self, farbe, konturen, params=None):
        self.farbe = farbe
        self.konturen = konturen
        self.params = {**FUELL_PARAMS, **(params or {})}

    def d(self):
        return " ".join(_teilpfad(k) + " Z" for k in self.konturen)

    def svg(self, id_):
        return (f'<path id="{id_}" d="{self.d()}" '
                f'style="fill:{_hex(self.farbe)};fill-rule:evenodd;stroke:none" '
                f'{_attribute(self.params)}/>')


def konturen(maske, mm_per_px, ursprung=(0, 0), glaetten=5, min_flaeche_mm2=1.0):
    """Konturen einer Pixelmaske als geglaettete Punktlisten in mm
    (Aussenkonturen und Loecher)."""
    ks, _ = cv2.findContours(maske.astype(np.uint8), cv2.RETR_CCOMP,
                             cv2.CHAIN_APPROX_NONE)
    out = []
    for k in ks:
        if cv2.contourArea(k) * mm_per_px ** 2 < min_flaeche_mm2:
            continue
        pts = (k[:, 0, :].astype(float) - ursprung) * mm_per_px
        pts = stiche.resample(pts, 0.3, closed=True)
        out.append(stiche.resample(stiche.smooth(pts, glaetten, closed=True),
                                   0.5, closed=True))
    return out


def dokument(ebenen, breite_mm, hoehe_mm):
    """ebenen: Liste von (Name, [Satin|Fuellung, ...]) in Stickreihenfolge."""
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'xmlns:inkstitch="http://inkstitch.org/namespace" '
        f'width="{breite_mm:.2f}mm" height="{hoehe_mm:.2f}mm" '
        f'viewBox="0 0 {breite_mm:.3f} {hoehe_mm:.3f}">',
    ]
    for n, (name, objekte) in enumerate(ebenen, 1):
        out.append(f'  <g id="ebene{n}" inkscape:groupmode="layer" '
                   f'inkscape:label="{n:02d} {name}">')
        for i, obj in enumerate(objekte, 1):
            out.append("    " + obj.svg(f"e{n}_{i}"))
        out.append("  </g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _breiten(mitte, neu, breite):
    """Breite (Zahl oder ein Wert pro Punkt von mitte) auf neue Punkte uebertragen."""
    if np.ndim(breite) == 0:
        return np.full(len(neu), float(breite))
    src = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(mitte, axis=0), axis=1))])
    dst = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(neu, axis=0), axis=1))])
    return np.interp(dst / max(dst[-1], 1e-9) * src[-1], src, np.asarray(breite, float))


def _halbbreite(c, n, h):
    """Begrenzt die halbe Breite auf einer Seite so, dass die Schiene in engen
    Innenkurven keine Schlaufe bildet: ein Schienenpunkt darf keinem anderen
    Punkt der Mittellinie naeher sein als seinem eigenen."""
    h = h.copy()
    for _ in range(3):
        p = c + n * h[:, None]
        dist = np.linalg.norm(p[:, None, :] - c[None, :, :], axis=2)
        np.fill_diagonal(dist, np.inf)
        dist = dist.min(axis=1)
        h = np.where(dist < h, dist * 0.95, h)
        h = np.minimum(h, np.convolve(np.pad(h, 2, mode="edge"),
                                      np.ones(5) / 5, mode="valid"))
    return h


def _teilpfad(pts):
    return "M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in pts)


def _hex(farbe):
    return "#{:02x}{:02x}{:02x}".format(*farbe)


def _attribute(params):
    return " ".join(f'inkstitch:{k}="{v}"' for k, v in params.items())
