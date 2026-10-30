"""Bausteine fuer Stichpfade: Geradstich, Satinstich, Vernaehen.

Alle Funktionen arbeiten mit Punktlisten in mm. Ein Pfad ist eine Folge von
Einstichpunkten, die ohne Sprung gestickt wird.
"""

import numpy as np


def resample(points, step, closed=False):
    """Verteilt Punkte gleichmaessig im Abstand step entlang der Linie."""
    pts = np.asarray(points, dtype=float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    dist = np.concatenate([[0.0], np.cumsum(seg)])
    total = dist[-1]
    if total == 0:
        return pts[:1]
    n = max(2, int(round(total / step)) + (0 if closed else 1))
    t = np.linspace(0, total, n, endpoint=not closed)
    return np.column_stack([np.interp(t, dist, pts[:, 0]),
                            np.interp(t, dist, pts[:, 1])])


def smooth(points, window, closed=False):
    """Gleitender Mittelwert ueber window Punkte (glaettet Pixelkanten)."""
    pts = np.asarray(points, dtype=float)
    if window < 2 or len(pts) < 3:
        return pts
    window = min(window, len(pts) - 1)
    if closed:
        pad = np.vstack([pts[-window:], pts, pts[:window]])
    else:
        pad = np.vstack([np.repeat(pts[:1], window, 0), pts,
                         np.repeat(pts[-1:], window, 0)])
    kernel = np.ones(window) / window
    out = np.column_stack([np.convolve(pad[:, i], kernel, mode="same")
                           for i in range(2)])
    out = out[window:-window]
    if not closed:
        out[0], out[-1] = pts[0], pts[-1]
    return out


def normals(points, closed=False):
    """Einheitsnormalen (nach links) entlang der Linie."""
    pts = np.asarray(points, dtype=float)
    if closed:
        tangent = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
    else:
        tangent = np.gradient(pts, axis=0)
    length = np.linalg.norm(tangent, axis=1, keepdims=True)
    tangent = tangent / np.maximum(length, 1e-9)
    return np.column_stack([-tangent[:, 1], tangent[:, 0]])


def running(points, length=2.0, closed=False):
    """Geradstich entlang der Linie mit Stichlaenge length."""
    pts = resample(points, length, closed)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    return pts


def satin(points, width, closed=False, spacing=0.4, underlay=True):
    """Satinstich (Raupe) entlang einer Mittellinie.

    width:   Breite in mm, Zahl oder ein Wert pro Punkt von points
    spacing: Abstand zweier Stiche auf derselben Seite (Dichte)
    underlay: vorher einen Geradstich entlang der Mitte als Unterlage sticken
    """
    pts = np.asarray(points, dtype=float)
    center = resample(pts, spacing / 2, closed)
    if np.ndim(width) == 0:
        widths = np.full(len(center), float(width))
    else:
        # Breiten von den Originalpunkten auf die neuen Punkte uebertragen
        src = np.concatenate([[0.0], np.cumsum(
            np.linalg.norm(np.diff(pts, axis=0), axis=1))])
        dst = np.concatenate([[0.0], np.cumsum(
            np.linalg.norm(np.diff(center, axis=0), axis=1))])
        widths = np.interp(dst / max(dst[-1], 1e-9) * src[-1], src,
                           np.asarray(width, dtype=float))
    side = np.where(np.arange(len(center)) % 2 == 0, 0.5, -0.5)
    zigzag = center + normals(center, closed) * (widths * side)[:, None]

    if not underlay:
        return zigzag
    under = running(pts, 1.5, closed)
    if closed:
        return np.vstack([under, zigzag, zigzag[:1]])
    # offen: Unterlage hin, Satin zurueck
    return np.vstack([under, zigzag[::-1]])


def lock(path, size=0.4):
    """Vernaeht Anfang und Ende mit kurzen Hin-und-her-Stichen."""
    pts = np.asarray(path, dtype=float)
    if len(pts) < 2:
        return pts

    def tie(p, q):
        d = q - p
        n = np.linalg.norm(d)
        step = d / n * min(size, n) if n else d
        return [p, p + step, p, p + step, p]

    return np.vstack([tie(pts[0], pts[1]), pts[1:-1],
                      tie(pts[-1], pts[-2])[::-1]])
