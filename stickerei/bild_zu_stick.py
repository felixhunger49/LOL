#!/usr/bin/env python3
"""Wandelt ein Bild (PNG, JPG, ...) in eine Stickdatei im SVG-Format um.

Ablauf:
  1. Bild laden und auf die Zielgroesse (in mm) bringen
  2. Farben auf wenige Garnfarben reduzieren (k-Means)
  3. Kleine Stoerflecken glaetten
  4. Jede Farbflaeche mit Fuellstichen (Tatami, Zickzack-Reihen) fuellen
  5. Stiche als SVG-Polylinien schreiben – eine Gruppe pro Garnfarbe

Jeder Punkt einer Polylinie ist ein Einstichpunkt. Eine neue Polylinie
bedeutet einen Sprungstich (Faden wird abgeschnitten / gesprungen).
Die Pfade sind fuer Ink/Stitch als "manuelle Stiche" markiert und lassen
sich dort direkt in DST, PES, JEF usw. exportieren.

Benoetigt: Pillow, numpy
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image


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
# Stiche erzeugen
# ---------------------------------------------------------------------------

def row_runs(mask, y_px, min_len_px):
    """Zusammenhaengende Bereiche (x_start, x_end) einer Maskenzeile."""
    row = mask[min(int(y_px), mask.shape[0] - 1)]
    padded = np.concatenate(([False], row, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    return [(a, b) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_len_px]


def stitches_along(x0, x1, y, max_len, offset):
    """Stichpunkte von x0 nach x1 auf Hoehe y. Zwischenpunkte liegen auf einem
    pro Reihe versetzten Raster, damit kein sichtbares Muster (Rille) entsteht."""
    step = 1 if x1 >= x0 else -1
    lo, hi = sorted((x0, x1))
    k_start = math.ceil((lo - offset) / max_len)
    k_end = math.floor((hi - offset) / max_len)
    inner = [offset + k * max_len for k in range(k_start, k_end + 1)]
    inner = [x for x in inner if lo + 0.3 * max_len < x < hi - 0.3 * max_len]
    if step < 0:
        inner.reverse()
    return [(x0, y)] + [(x, y) for x in inner] + [(x1, y)]


def fill_region(mask, spacing, max_len, min_len):
    """Fuellt eine Maske mit Tatami-Reihen. Werte in Pixel-Einheiten.
    Liefert eine Liste von Bloecken; jeder Block ist eine Punktliste,
    die ohne Sprung gestickt werden kann."""
    h = mask.shape[0]
    ys = np.arange(spacing / 2, h, spacing)
    rows = [row_runs(mask, y, min_len) for y in ys]
    used = [[False] * len(r) for r in rows]
    blocks = []

    for start_row in range(len(rows)):
        for start_idx in range(len(rows[start_row])):
            if used[start_row][start_idx]:
                continue
            # Block bilden: Reihe fuer Reihe nach unten, solange ein
            # ueberlappender, noch freier Abschnitt existiert.
            points = []
            r, idx, forward = start_row, start_idx, True
            while True:
                used[r][idx] = True
                a, b = rows[r][idx]
                x0, x1 = (a, b) if forward else (b, a)
                offset = (r % 3) * max_len / 3
                points.extend(stitches_along(x0, x1, ys[r], max_len, offset))
                if r + 1 >= len(rows):
                    break
                nxt = [i for i, (c, d) in enumerate(rows[r + 1])
                       if not used[r + 1][i] and c < b and d > a]
                if not nxt:
                    break
                # den Abschnitt nehmen, der auf der aktuellen Endseite liegt
                end_x = x1
                idx = min(nxt, key=lambda i: min(abs(rows[r + 1][i][0] - end_x),
                                                 abs(rows[r + 1][i][1] - end_x)))
                r += 1
                forward = not forward
            blocks.append(points)
    return blocks


def order_blocks(blocks):
    """Sortiert Bloecke nach naechstem Nachbarn, um Spruenge kurz zu halten."""
    remaining = list(blocks)
    ordered = []
    pos = (0.0, 0.0)
    while remaining:
        best_i, best_rev, best_d = 0, False, float("inf")
        for i, blk in enumerate(remaining):
            for rev, pt in ((False, blk[0]), (True, blk[-1])):
                d = (pt[0] - pos[0]) ** 2 + (pt[1] - pos[1]) ** 2
                if d < best_d:
                    best_i, best_rev, best_d = i, rev, d
        blk = remaining.pop(best_i)
        if best_rev:
            blk = blk[::-1]
        ordered.append(blk)
        pos = blk[-1]
    return ordered


def merge_close_blocks(blocks, max_jump):
    """Verbindet aufeinanderfolgende Bloecke, wenn der Abstand klein ist
    (dann wird einfach weitergestickt statt gesprungen)."""
    merged = []
    for blk in blocks:
        if merged:
            last = merged[-1][-1]
            if math.dist(last, blk[0]) <= max_jump:
                merged[-1].extend(blk)
                continue
        merged.append(list(blk))
    return merged


# ---------------------------------------------------------------------------
# SVG schreiben
# ---------------------------------------------------------------------------

def to_svg(layers, width_mm, height_mm, thread_mm):
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'xmlns:inkstitch="http://inkstitch.org/namespace" '
        f'width="{width_mm:.2f}mm" height="{height_mm:.2f}mm" '
        f'viewBox="0 0 {width_mm:.3f} {height_mm:.3f}">',
    ]
    for n, (color, paths) in enumerate(layers, 1):
        hexcol = "#{:02x}{:02x}{:02x}".format(*color)
        out.append(f'  <g id="farbe{n}" inkscape:groupmode="layer" '
                   f'inkscape:label="Farbe {n} {hexcol}">')
        for i, pts in enumerate(paths):
            d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
            out.append(
                f'    <path id="farbe{n}_{i}" d="{d}" fill="none" '
                f'stroke="{hexcol}" stroke-width="{thread_mm}" '
                f'stroke-linejoin="round" stroke-linecap="round" '
                f'inkstitch:stroke_method="manual_stitch" '
                f'inkstitch:manual_stitch="true"/>')
        out.append("  </g>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


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

    to_px = 1 / mm_per_px
    layers, total, jumps = [], 0, 0
    # helle Farben zuerst sticken, dunkle (Konturen) zuletzt obendrauf
    order = sorted(range(len(palette)), key=lambda i: -int(palette[i].astype(int).sum()))
    for i in order:
        if i in skip:
            continue
        mask = (labels == i) & opaque
        if mask.sum() * mm_per_px ** 2 < args.min_flaeche:
            continue
        blocks = fill_region(mask, args.reihenabstand * to_px,
                             args.stichlaenge * to_px, args.min_laenge * to_px)
        blocks = merge_close_blocks(order_blocks(blocks), args.max_verbindung * to_px)
        paths = [[(x * mm_per_px, y * mm_per_px) for x, y in blk]
                 for blk in blocks if len(blk) > 1]
        if not paths:
            continue
        layers.append((tuple(int(c) for c in palette[i]), paths))
        total += sum(len(p) for p in paths)
        jumps += len(paths) - 1

    out = Path(args.ausgabe or Path(args.bild).with_suffix(".svg"))
    out.write_text(to_svg(layers, args.breite, height_mm, args.reihenabstand))

    print(f"Gespeichert: {out}")
    print(f"Groesse:     {args.breite:.1f} x {height_mm:.1f} mm")
    print(f"Farben:      {len(layers)}")
    print(f"Stiche:      {total}")
    print(f"Spruenge:    {jumps}")
    for n, (color, paths) in enumerate(layers, 1):
        print(f"  Farbe {n}: #{color[0]:02x}{color[1]:02x}{color[2]:02x} "
              f"– {sum(len(p) for p in paths)} Stiche")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Erstellt aus einem Bild eine Stickdatei im SVG-Format.")
    p.add_argument("bild", help="Eingabebild (PNG, JPG, ...)")
    p.add_argument("-o", "--ausgabe", help="Ziel-SVG (Standard: Bildname.svg)")
    p.add_argument("-b", "--breite", type=float, default=80,
                   help="Breite des Motivs in mm (Standard: 80)")
    p.add_argument("-f", "--farben", type=int, default=6,
                   help="Anzahl Garnfarben inkl. Hintergrund (Standard: 6)")
    p.add_argument("--mit-hintergrund", action="store_true",
                   help="Hintergrundfarbe ebenfalls aussticken")
    p.add_argument("--reihenabstand", type=float, default=0.4,
                   help="Abstand der Fuellreihen in mm (Standard: 0.4)")
    p.add_argument("--stichlaenge", type=float, default=3.0,
                   help="Maximale Stichlaenge in mm (Standard: 3.0)")
    p.add_argument("--min-laenge", type=float, default=0.8,
                   help="Kuerzere Reihenstuecke weglassen, in mm (Standard: 0.8)")
    p.add_argument("--min-flaeche", type=float, default=4.0,
                   help="Kleinere Farbflaechen weglassen, in mm² (Standard: 4)")
    p.add_argument("--max-verbindung", type=float, default=2.0,
                   help="Bis zu diesem Abstand (mm) weitersticken statt springen")
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
