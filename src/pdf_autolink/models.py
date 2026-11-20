"""Plain data types shared by every stage. No PDF library imports here."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class WordBox:
    """A word in DISPLAY coordinates: points, top-left origin, after /Rotate, relative to CropBox."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float


@dataclass(frozen=True)
class PageText:
    index: int  # 0-based
    width: float  # display size (after rotation)
    height: float
    words: list[WordBox]


class RefKind(StrEnum):
    SHEET = "sheet"
    DETAIL = "detail"


class Status(StrEnum):
    LINKED = "linked"
    UNMATCHED = "unmatched"
    SELF = "self"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Reference:
    page: int  # 0-based source page
    text: str  # verbatim: "A101" or "3/A501"
    kind: RefKind
    code: str  # normalized target sheet code
    rect: tuple[float, float, float, float]  # display coords, top-left origin (x0, y0, x1, y1)


@dataclass(frozen=True)
class Resolved:
    ref: Reference
    status: Status
    target_page: int | None  # 0-based


@dataclass
class SheetIndex:
    by_code: dict[str, list[int]]  # code -> 0-based pages
    unrecognized: list[int]
    page_codes: dict[int, str | None]


@dataclass
class Result:
    sheets: SheetIndex
    resolved: list[Resolved]
    links_added: int
    links_skipped_existing: int


class PdfAutolinkError(Exception):
    """Unreadable / encrypted / empty input, or output path equal to input."""
