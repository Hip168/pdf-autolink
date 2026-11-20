"""Dựng PDF bản vẽ mẫu cho test (reportlab + pikepdf).

Quy ước (độc lập với ``pdf_autolink.geometry``):

* ``PageSpec.size``    = MediaBox ``(w, h)`` chưa xoay, gốc (0, 0).
* ``PageSpec.cropbox`` = ``(x0, y0, x1, y1)`` trong user space PDF, hoặc None.
* ``PageSpec.rotate``  = ``/Rotate`` (0/90/180/270, chiều kim đồng hồ).
* ``PageSpec.texts``   = ``(x, y, size, text)`` theo toạ độ HIỂN THỊ:
  gốc trên-trái vùng nhìn thấy (CropBox sau xoay), ``y`` là đường cơ sở
  tính từ mép trên. Chữ luôn nằm ngang (đọc xuôi) trên hiển thị.
* ``PageSpec.code``    = mã trang, vẽ cỡ 24 ở góc dưới phải hiển thị.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pikepdf
from reportlab.pdfgen import canvas

CODE_SIZE = 24.0
LETTER = (612.0, 792.0)


@dataclass
class PageSpec:
    code: str | None = None
    texts: list[tuple[float, float, float, str]] = field(default_factory=list)
    rotate: int = 0
    cropbox: tuple[float, float, float, float] | None = None
    size: tuple[float, float] = LETTER

    def visible(self) -> tuple[float, float, float, float]:
        if self.cropbox is not None:
            return self.cropbox
        return (0.0, 0.0, self.size[0], self.size[1])

    def display_size(self) -> tuple[float, float]:
        x0, y0, x1, y1 = self.visible()
        w, h = x1 - x0, y1 - y0
        return (h, w) if self.rotate in (90, 270) else (w, h)


def to_user_space(spec: PageSpec, xd: float, yd: float) -> tuple[float, float]:
    """Điểm hiển thị (xd, yd từ mép trên) -> user space PDF."""
    cx0, cy0, cx1, cy1 = spec.visible()
    cw, ch = cx1 - cx0, cy1 - cy0
    if spec.rotate == 0:
        xr, yr = xd, ch - yd
    elif spec.rotate == 90:
        xr, yr = yd, xd
    elif spec.rotate == 180:
        xr, yr = cw - xd, yd
    elif spec.rotate == 270:
        xr, yr = cw - yd, ch - xd
    else:
        raise ValueError(f"rotate không hợp lệ: {spec.rotate}")
    return cx0 + xr, cy0 + yr


def build(pages: list[PageSpec], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + "._raw.pdf")
    c = canvas.Canvas(str(tmp), pagesize=pages[0].size if pages else LETTER)
    for spec in pages:
        c.setPageSize(spec.size)
        items = list(spec.texts)
        if spec.code:
            dw, dh = spec.display_size()
            items.insert(0, (dw - 110.0, dh - 30.0, CODE_SIZE, spec.code))
        for xd, yd, size, text in items:
            ux, uy = to_user_space(spec, xd, yd)
            c.saveState()
            c.translate(ux, uy)
            c.rotate(spec.rotate)
            c.setFont("Helvetica", size)
            c.drawString(0, 0, text)
            c.restoreState()
        c.showPage()
    c.save()
    with pikepdf.open(tmp) as pdf:
        for page, spec in zip(pdf.pages, pages, strict=True):
            if spec.rotate:
                page.obj["/Rotate"] = spec.rotate
            if spec.cropbox is not None:
                page.obj["/CropBox"] = pikepdf.Array(list(spec.cropbox))
        pdf.save(path)
    tmp.unlink()
    return path


def links(
    pdf: pikepdf.Pdf, index: int
) -> list[tuple[tuple[float, ...], int | None, pikepdf.Object]]:
    """Các /Link GoTo của trang ``index``: (rect, trang đích 0-based, annot)."""
    out = []
    annots = pdf.pages[index].obj.get("/Annots")
    for annot in annots or []:
        if str(annot.get("/Subtype")) != "/Link":
            continue
        action = annot.get("/A")
        if action is None or str(action.get("/S")) != "/GoTo":
            continue
        dest = action["/D"][0]
        target = next((i for i, p in enumerate(pdf.pages) if p.objgen == dest.objgen), None)
        rect = tuple(float(v) for v in annot["/Rect"])
        out.append((rect, target, annot))
    return out


def count_links(pdf: pikepdf.Pdf) -> int:
    return sum(len(links(pdf, i)) for i in range(len(pdf.pages)))
