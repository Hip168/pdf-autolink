"""Text extraction: words with display coordinates."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pdfplumber

from .models import PageText, WordBox


class TextSource(Protocol):
    def pages(self) -> Iterator[PageText]: ...


def _norm(box) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = (float(v) for v in box)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _crop_origin(mediabox, cropbox, rotate: int) -> tuple[float, float]:
    """Top-left corner of the CropBox in pdfminer's rotated MediaBox frame (top-left origin).

    pdfplumber reports words in that frame, ignoring the CropBox; its own ``cropbox``
    attribute is wrong for /Rotate 180 and 270, so it is recomputed here.
    """
    mx0, my0, mx1, my1 = mediabox
    cx0, cy0, cx1, cy1 = cropbox
    if rotate == 90:
        return cy0 - my0, cx0 - mx0
    if rotate == 180:
        return mx1 - cx1, cy0 - my0
    if rotate == 270:
        return my1 - cy1, mx1 - cx1
    return cx0 - mx0, my1 - cy1


class PdfplumberSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def pages(self) -> Iterator[PageText]:
        with pdfplumber.open(self.path) as doc:
            for i, page in enumerate(doc.pages):
                rotate = page.rotation
                mediabox = _norm(page.page_obj.mediabox)
                cropbox = _norm(page.page_obj.cropbox or mediabox)
                ox, oy = _crop_origin(mediabox, cropbox, rotate)
                ox += page.mediabox[0]  # pdfplumber shifts words by its own MediaBox corner
                oy += page.mediabox[1]
                cw, ch = cropbox[2] - cropbox[0], cropbox[3] - cropbox[1]
                width, height = (ch, cw) if rotate in (90, 270) else (cw, ch)
                words = [
                    WordBox(
                        text=w["text"],
                        x0=w["x0"] - ox,
                        y0=w["top"] - oy,
                        x1=w["x1"] - ox,
                        y1=w["bottom"] - oy,
                        size=float(w["size"]),
                    )
                    for w in page.extract_words(extra_attrs=["size"])
                ]
                page.close()  # free pdfminer layout cache; memory stays flat on big sets
                yield PageText(index=i, width=width, height=height, words=words)
