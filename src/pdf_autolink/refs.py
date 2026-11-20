"""Find sheet references and detail callouts on a page (pure logic)."""

from __future__ import annotations

import re

from .config import Config, normalize_code
from .models import PageText, Reference, RefKind, WordBox
from .sheetid import in_title_block

_DIGITS = re.compile(r"\d{1,3}")


def _union(words: list[WordBox]) -> tuple[float, float, float, float]:
    return (
        min(w.x0 for w in words),
        min(w.y0 for w in words),
        max(w.x1 for w in words),
        max(w.y1 for w in words),
    )


def _next_on_line(word: WordBox, words: list[WordBox], used: set[int]) -> int | None:
    """Index of the nearest unused word just right of ``word`` on the same line."""
    cy = (word.y0 + word.y1) / 2
    best: int | None = None
    for i, w in enumerate(words):
        if i in used or w is word or w.x0 < word.x0:
            continue
        gap = w.x0 - word.x1
        same_line = abs((w.y0 + w.y1) / 2 - cy) <= max(w.y1 - w.y0, word.y1 - word.y0) / 2
        if same_line and gap <= word.size and (best is None or w.x0 < words[best].x0):
            best = i
    return best


def find_references(page: PageText, own_code: str | None, cfg: Config) -> list[Reference]:
    sheet_re = re.compile(cfg.sheet_regex)
    detail_re = re.compile(cfg.detail_regex.replace("{sheet}", cfg.sheet_regex))
    words = [
        w
        for w in page.words
        if not (
            own_code is not None
            and sheet_re.fullmatch(w.text)
            and normalize_code(w.text) == own_code
            and in_title_block(w, page, cfg)
        )
    ]
    used: set[int] = set()
    refs: list[Reference] = []

    def emit(idxs: list[int], text: str, kind: RefKind, code: str) -> None:
        used.update(idxs)
        rect = _union([words[i] for i in idxs])
        refs.append(Reference(page.index, text, kind, normalize_code(code), rect))

    # (1) one-line detail: a single word, or 2-3 adjacent words on the same line.
    for i, w in enumerate(words):
        if i in used:
            continue
        chain = [i]
        while True:
            text = "".join(words[j].text for j in chain)
            m = detail_re.fullmatch(text)
            if m:
                emit(chain, text, RefKind.DETAIL, m.group(2))
                break
            if len(chain) == 3:
                break
            nxt = _next_on_line(words[chain[-1]], words, used | set(chain))
            if nxt is None:
                break
            chain.append(nxt)

    # (2) two-line detail: 1-3 digits with a sheet code just below.
    for i in sorted(range(len(words)), key=lambda k: words[k].y0):
        top = words[i]
        if i in used or not _DIGITS.fullmatch(top.text):
            continue
        best: int | None = None
        best_gap = 0.0
        for j, low in enumerate(words):
            if j in used or j == i or not sheet_re.fullmatch(low.text):
                continue
            size = max(top.size, low.size)
            gap = low.y0 - top.y1
            below = (low.y0 + low.y1) / 2 > (top.y0 + top.y1) / 2
            overlap_x = low.x0 <= top.x1 and top.x0 <= low.x1
            centre_dx = abs((low.x0 + low.x1) / 2 - (top.x0 + top.x1) / 2)
            if (
                below
                and gap <= cfg.stack_max_gap_factor * size
                and (overlap_x or centre_dx <= 2 * size)
                and (best is None or gap < best_gap)
            ):
                best, best_gap = j, gap
        if best is not None:
            emit([i, best], f"{top.text}/{words[best].text}", RefKind.DETAIL, words[best].text)

    # (3) remaining bare sheet codes.
    for i, w in enumerate(words):
        if i not in used and sheet_re.fullmatch(w.text):
            emit([i], w.text, RefKind.SHEET, w.text)

    refs.sort(key=lambda r: (r.rect[1], r.rect[0]))
    return refs
