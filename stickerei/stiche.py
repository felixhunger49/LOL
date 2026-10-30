"""Geometrie-Helfer fuer Linien (Punktlisten in mm): gleichmaessig verteilen,
glaetten, Normalen berechnen."""

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
