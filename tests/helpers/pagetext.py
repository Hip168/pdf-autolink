"""Dựng PageText / WordBox bằng tay cho test logic thuần (không cần PDF)."""

from __future__ import annotations

from pdf_autolink.models import PageText, WordBox

PAGE_W = 612.0
PAGE_H = 792.0
CHAR_W = 0.55  # bề rộng ký tự ~ 0.55 * cỡ chữ


def word(text: str, x: float, y: float, size: float = 10.0) -> WordBox:
    """Từ có góc trên-trái (x, y) hiển thị, cao = size, rộng = 0.55*size*len."""
    return WordBox(
        text=text,
        x0=x,
        y0=y,
        x1=x + CHAR_W * size * len(text),
        y1=y + size,
        size=size,
    )


def page(
    words: list[WordBox],
    index: int = 0,
    width: float = PAGE_W,
    height: float = PAGE_H,
) -> PageText:
    return PageText(index=index, width=width, height=height, words=list(words))


def title(code: str, size: float = 24.0, index: int = 0) -> PageText:
    """Trang chỉ có mã ở khung tên (góc dưới phải)."""
    return page([word(code, 500.0, 740.0, size)], index=index)
