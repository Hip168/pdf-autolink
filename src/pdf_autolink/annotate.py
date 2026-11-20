"""Write /Link GoTo annotations with pikepdf (idempotent)."""

from __future__ import annotations

from collections.abc import Sequence

import pikepdf

from .config import Config
from .geometry import Rect, display_to_pdf_rect
from .models import PageText, Resolved, Status


def _iou(a: Rect, b: Rect) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _existing_goto(page: pikepdf.Page) -> list[tuple[Rect, tuple[int, int]]]:
    """(rect, objgen of target page) for each /Link GoTo already on the page."""
    out = []
    for annot in page.obj.get("/Annots") or []:
        if annot.get("/Subtype") != pikepdf.Name.Link:
            continue
        action = annot.get("/A")
        if action is None or action.get("/S") != pikepdf.Name.GoTo:
            continue
        dest = action.get("/D")
        if not isinstance(dest, pikepdf.Array) or len(dest) == 0 or "/Rect" not in annot:
            continue
        x0, y0, x1, y1 = (float(v) for v in annot["/Rect"])
        out.append(((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), dest[0].objgen))
    return out


def add_links(
    pdf: pikepdf.Pdf, resolved: Sequence[Resolved], pages: Sequence[PageText], cfg: Config
) -> tuple[int, int]:
    """Add a /Link for every LINKED reference. Returns (added, skipped_existing).

    ``pages`` is part of the public signature; rectangles are converted using the
    CropBox and /Rotate read from ``pdf`` itself.
    """
    added = skipped = 0
    existing: dict[int, list[tuple[Rect, tuple[int, int]]]] = {}
    for res in resolved:
        if res.status is not Status.LINKED or res.target_page is None:
            continue
        page = pdf.pages[res.ref.page]
        target = pdf.pages[res.target_page].obj
        cropbox = tuple(float(v) for v in page.cropbox)
        rect = display_to_pdf_rect(res.ref.rect, cropbox=cropbox, rotate=page.rotation)
        found = existing.setdefault(res.ref.page, _existing_goto(page))
        if any(
            gen == target.objgen and _iou(rect, r) >= cfg.iou_duplicate for r, gen in found
        ):
            skipped += 1
            continue
        annot = pdf.make_indirect(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Annot,
                Subtype=pikepdf.Name.Link,
                Rect=pikepdf.Array(list(rect)),
                Border=pikepdf.Array([0, 0, 0]),
                A=pikepdf.Dictionary(
                    S=pikepdf.Name.GoTo, D=pikepdf.Array([target, pikepdf.Name.Fit])
                ),
            )
        )
        if "/Annots" not in page.obj:
            page.obj["/Annots"] = pikepdf.Array()
        page.obj["/Annots"].append(annot)
        found.append((rect, target.objgen))
        added += 1
    return added, skipped
