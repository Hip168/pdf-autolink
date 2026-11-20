"""Find each page's own sheet number in its title block (pure logic)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .config import Config, normalize_code
from .models import PageText, SheetIndex, WordBox


def in_title_block(word: WordBox, page: PageText, cfg: Config) -> bool:
    """True when the word's centre lies inside ``cfg.title_block_region``."""
    rx0, ry0, rx1, ry1 = cfg.title_block_region
    cx = (word.x0 + word.x1) / 2 / page.width
    cy = (word.y0 + word.y1) / 2 / page.height
    return rx0 <= cx <= rx1 and ry0 <= cy <= ry1


def identify_sheet(page: PageText, cfg: Config) -> str | None:
    if page.width <= 0 or page.height <= 0:
        return None
    pattern = re.compile(cfg.sheet_regex)
    candidates = [
        w for w in page.words if pattern.fullmatch(w.text) and in_title_block(w, page, cfg)
    ]
    if not candidates:
        return None
    # Largest font; tie -> lowest on the page; then rightmost.
    best = max(candidates, key=lambda w: (w.size, w.y0 + w.y1, w.x0 + w.x1))
    return normalize_code(best.text)


def identify_all(pages: Sequence[PageText], cfg: Config) -> SheetIndex:
    index = SheetIndex(by_code={}, unrecognized=[], page_codes={})
    for page in pages:
        code = identify_sheet(page, cfg)
        index.page_codes[page.index] = code
        if code is None:
            index.unrecognized.append(page.index)
        else:
            index.by_code.setdefault(code, []).append(page.index)
    return index
