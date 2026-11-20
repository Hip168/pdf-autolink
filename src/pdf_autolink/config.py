"""Tunable settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Fractions of the display page, top-left origin: (x0, y0, x1, y1).
    title_block_region: tuple[float, float, float, float] = (0.55, 0.70, 1.0, 1.0)
    sheet_regex: str = r"[A-Z]{1,2}[-.]?\d{1,4}(?:[.\-]\d{1,3})?"
    detail_regex: str = r"(\d{1,3})\s*/\s*({sheet})"  # {sheet} is replaced by sheet_regex
    stack_max_gap_factor: float = 1.5
    iou_duplicate: float = 0.9


def normalize_code(text: str) -> str:
    """Upper-case and drop whitespace; keep '.' and '-' (A-501 != A501)."""
    return "".join(text.split()).upper()
