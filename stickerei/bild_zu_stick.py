#!/usr/bin/env python3
"""Wandelt ein Bild (PNG, JPG, ...) in eine Stickdatei fuer Inkscape/Ink/Stitch um.

Ablauf:
  1. Bild laden und auf die Zielgroesse (in mm) bringen
  2. Farben auf wenige Garnfarben reduzieren (k-Means)
  3. Kleine Stoerflecken glaetten
  4. Jede Farbflaeche als Ink/Stitch-Fuellflaeche (Tatami) ins SVG schreiben,
     eine Ebene pro Garnfarbe

Die Stiche berechnet Ink/Stitch beim Export (DST, PES, JEF, ...).

Benoetigt: pillow, numpy, opencv-python-headless
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from inkstitch import Fuellung, dokument, konturen


# ---------------------------------------------------------------------------
# Bild vorbereiten
# ---------------------------------------------------------------------------

def load_image(path, width_mm, px_per_mm):
    """Laedt das Bild, skaliert es auf width_mm (Raster px_per_mm) und
    liefert (RGB-Array, Alpha-Maske, mm pro Pixel)."""
    img = Image.open(path).convert("RGBA")
    w_px = max(1, round(width_mm * px_per_mm))
    h_px = max(1, round(img.height * w_px / img.width))
    img = img.resize((w_px, h_px), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32)
    return arr[:, :, :3], arr[:, :, 3] >= 128, width_mm / w_px


def kmeans_colors(pixels, k, iterations=20, seed=0):
    """Einfaches k-Means auf RGB-Pixeln. Liefert (Palette, Labels)."""
    rng = np.random.default_rng(seed)
    sample = pixels
    if len(sample) > 20000:
        sample = sample[rng.choice(len(sample), 20000, replace=False)]

    # k-Means++ Initialisierung
    centers = [sample[rng.integers(len(sample))]]
    for _ in range(1, k):
        d = np.min([((sample - c) ** 2).sum(1) for c in centers], axis=0)
        if d.sum() == 0:
            break
        centers.append(sample[rng.choice(len(sample), p=d / d.sum())])
    centers = np.array(centers)

    for _ in range(iterations):
        labels = ((sample[:, None, :] - centers[None]) ** 2).sum(2).argmin(1)
        new = np.array([
            sample[labels == i].mean(0) if np.any(labels == i) else centers[i]
            for i in range(len(centers))
        ])
        if np.allclose(new, centers, atol=0.5):
            break
        centers = new

    labels = np.empty(len(pixels), dtype=np.int32)
    for start in range(0, len(pixels), 50000):
        chunk = pixels[start:start + 50000]
        labels[start:start + 50000] = (
            (chunk[:, None, :] - centers[None]) ** 2).sum(2).argmin(1)
    return centers.round().astype(np.uint8), labels


def majority_filter(labels, n_labels, passes):
    """Ersetzt jedes Pixel durch das haeufigste Label seiner 3x3-Nachbarschaft.
    Entfernt Rauschen und Fransen, die sich schlecht sticken lassen."""
    h, w = labels.shape
    for _ in range(passes):
        padded = np.pad(labels, 1, mode="edge")
        counts = np.zeros((n_labels, h, w), dtype=np.uint8)
        for dy in range(3):
            for dx in range(3):
                window = padded[dy:dy + h, dx:dx + w]
                for i in range(n_labels):
                    counts[i] += window == i
        labels = counts.argmax(0).astype(labels.dtype)
    return labels


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def convert(args):
    rgb, opaque, mm_per_px = load_image(args.bild, args.breite, args.aufloesung)
    h_px, w_px = opaque.shape
    height_mm = h_px * mm_per_px

    palette, flat = kmeans_colors(rgb.reshape(-1, 3), args.farben)
    labels = majority_filter(flat.reshape(h_px, w_px), len(palette), args.glaetten)

    # Hintergrund bestimmen: haeufigste Farbe am Bildrand
    skip = set()
    if not args.mit_hintergrund:
        border = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
        skip.add(int(np.bincount(border, minlength=len(palette)).argmax()))

    params = {"row_spacing_mm": args.reihenabstand,
              "max_stitch_length_mm": args.stichlaenge}
    ebenen = []
    # helle Farben zuerst sticken, dunkle (Konturen) zuletzt obendrauf
    order = sorted(range(len(palette)), key=lambda i: -int(palette[i].astype(int).sum()))
    for i in order:
        if i in skip:
            continue
        mask = (labels == i) & opaque
        ks = konturen(mask, mm_per_px, min_flaeche_mm2=args.min_flaeche)
        if not ks:
            continue
        farbe = tuple(int(c) for c in palette[i])
        ebenen.append(("Farbe {} #{:02x}{:02x}{:02x}".format(len(ebenen) + 1, *farbe),
                       [Fuellung(farbe, ks, params)]))

    out = Path(args.ausgabe or Path(args.bild).with_suffix(".svg"))
    out.write_text(dokument(ebenen, args.breite, height_mm))

    print(f"Gespeichert: {out}")
    print(f"Groesse:     {args.breite:.1f} x {height_mm:.1f} mm")
    print(f"Farben:      {len(ebenen)}")
    for name, _ in ebenen:
        print(f"  {name}")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Erstellt aus einem Bild eine Stickdatei (SVG fuer Ink/Stitch).")
    p.add_argument("bild", help="Eingabebild (PNG, JPG, ...)")
    p.add_argument("-o", "--ausgabe", help="Ziel-SVG (Standard: Bildname.svg)")
    p.add_argument("-b", "--breite", type=float, default=80,
                   help="Breite des Motivs in mm (Standard: 80)")
    p.add_argument("-f", "--farben", type=int, default=6,
                   help="Anzahl Garnfarben inkl. Hintergrund (Standard: 6)")
    p.add_argument("--mit-hintergrund", action="store_true",
                   help="Hintergrundfarbe ebenfalls aussticken")
    p.add_argument("--reihenabstand", type=float, default=0.25,
                   help="Abstand der Fuellreihen in mm (Standard: 0.25)")
    p.add_argument("--stichlaenge", type=float, default=3.0,
                   help="Maximale Stichlaenge in mm (Standard: 3.0)")
    p.add_argument("--min-flaeche", type=float, default=4.0,
                   help="Kleinere Farbflaechen weglassen, in mm² (Standard: 4)")
    p.add_argument("--glaetten", type=int, default=2,
                   help="Durchgaenge des Glaettungsfilters (Standard: 2)")
    p.add_argument("--aufloesung", type=float, default=10,
                   help="Rasterpunkte pro mm fuer die Analyse (Standard: 10)")
    args = p.parse_args(argv)

    if args.farben < 2:
        p.error("--farben muss mindestens 2 sein")
    try:
        convert(args)
    except FileNotFoundError:
        sys.exit(f"Bild nicht gefunden: {args.bild}")


if __name__ == "__main__":
    main()
