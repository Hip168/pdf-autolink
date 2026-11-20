"""[1-1] models.py + config.py + __init__ re-export."""

from __future__ import annotations

import dataclasses
import re

import pytest

import pdf_autolink
from pdf_autolink.config import Config, normalize_code
from pdf_autolink.models import (
    PageText,
    PdfAutolinkError,
    Reference,
    RefKind,
    Resolved,
    Result,
    SheetIndex,
    Status,
    WordBox,
)


def test_package_reexports_public_api():
    from pdf_autolink import Config as C
    from pdf_autolink import PdfAutolinkError as E
    from pdf_autolink import autolink

    assert C is Config
    assert E is PdfAutolinkError
    assert callable(autolink)
    assert isinstance(pdf_autolink.__version__, str)
    assert pdf_autolink.__version__


def test_pdf_autolink_error_is_exception():
    assert issubclass(PdfAutolinkError, Exception)


def test_enum_values_are_lowercase_strings():
    assert RefKind.SHEET == "sheet"
    assert RefKind.DETAIL == "detail"
    assert Status.LINKED == "linked"
    assert Status.UNMATCHED == "unmatched"
    assert Status.SELF == "self"
    assert Status.AMBIGUOUS == "ambiguous"
    assert str(Status.LINKED) == "linked"


def test_models_are_frozen():
    w = WordBox("A", 0, 0, 1, 1, 10)
    with pytest.raises(dataclasses.FrozenInstanceError):
        w.text = "B"  # type: ignore[misc]
    ref = Reference(0, "A101", RefKind.SHEET, "A101", (0, 0, 1, 1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        ref.code = "X"  # type: ignore[misc]
    res = Resolved(ref, Status.LINKED, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.status = Status.SELF  # type: ignore[misc]


def test_pagetext_and_result_fields():
    pt = PageText(index=2, width=612, height=792, words=[])
    assert (pt.index, pt.width, pt.height, pt.words) == (2, 612, 792, [])
    idx = SheetIndex(by_code={"A101": [0]}, unrecognized=[1], page_codes={0: "A101", 1: None})
    r = Result(sheets=idx, resolved=[], links_added=3, links_skipped_existing=1)
    assert r.sheets.by_code == {"A101": [0]}
    assert r.sheets.unrecognized == [1]
    assert r.links_added == 3
    assert r.links_skipped_existing == 1


def test_config_defaults_match_contract():
    cfg = Config()
    assert cfg.title_block_region == (0.55, 0.70, 1.0, 1.0)
    assert cfg.sheet_regex == r"[A-Z]{1,2}[-.]?\d{1,4}(?:[.\-]\d{1,3})?"
    assert cfg.detail_regex == r"(\d{1,3})\s*/\s*({sheet})"
    assert cfg.stack_max_gap_factor == 1.5
    assert cfg.iou_duplicate == 0.9


def test_config_is_frozen_and_overridable():
    cfg = Config(stack_max_gap_factor=3.0)
    assert cfg.stack_max_gap_factor == 3.0
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.iou_duplicate = 0.5  # type: ignore[misc]


@pytest.mark.parametrize("code", ["A101", "M201", "S-101", "E0.01", "AB12", "A1.2-3"])
def test_default_sheet_regex_accepts_drawing_codes(code):
    assert re.fullmatch(Config().sheet_regex, code)


@pytest.mark.parametrize("text", ["ABC1", "101", "A", "a101", "A12345", "SCALE", "A101X"])
def test_default_sheet_regex_rejects_non_codes(text):
    assert not re.fullmatch(Config().sheet_regex, text)


def test_detail_regex_with_sheet_placeholder_captures_number_and_code():
    cfg = Config()
    pattern = cfg.detail_regex.replace("{sheet}", cfg.sheet_regex)
    m = re.fullmatch(pattern, "3/A501")
    assert m is not None
    assert m.group(1) == "3"
    assert m.group(2) == "A501"
    assert re.fullmatch(pattern, "12 / S-101") is not None
    assert re.fullmatch(pattern, "3A501") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A101", "A101"),
        ("a101", "A101"),
        (" a 101 ", "A101"),
        ("s-101", "S-101"),
        ("e0.01", "E0.01"),
        ("A\t501", "A501"),
    ],
)
def test_normalize_code_uppercases_and_strips_whitespace(raw, expected):
    assert normalize_code(raw) == expected


def test_normalize_code_keeps_dash_so_a_dash_501_differs_from_a501():
    assert normalize_code("A-501") == "A-501"
    assert normalize_code("A-501") != normalize_code("A501")
