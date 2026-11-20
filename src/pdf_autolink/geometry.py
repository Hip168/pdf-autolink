"""Display coordinates <-> PDF user space."""

from __future__ import annotations

Rect = tuple[float, float, float, float]


def display_to_pdf_rect(rect: Rect, *, cropbox: Rect, rotate: int) -> Rect:
    """Map a display rect (top-left origin, after /Rotate, relative to CropBox) to user space.

    /Rotate turns the page clockwise for display. Returns (x0, y0, x1, y1) with x0<x1, y0<y1.
    """
    cx0, cy0 = min(cropbox[0], cropbox[2]), min(cropbox[1], cropbox[3])
    w = abs(cropbox[2] - cropbox[0])  # unrotated CropBox size
    h = abs(cropbox[3] - cropbox[1])
    rot = rotate % 360

    def point(x: float, y: float) -> tuple[float, float]:
        if rot == 90:
            u, v = y, x
        elif rot == 180:
            u, v = w - x, y
        elif rot == 270:
            u, v = w - y, h - x
        else:
            u, v = x, h - y
        return u + cx0, v + cy0

    ax, ay = point(rect[0], rect[1])
    bx, by = point(rect[2], rect[3])
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)
