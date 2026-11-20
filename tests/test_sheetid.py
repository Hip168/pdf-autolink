"""[1-2] identify_sheet / identify_all."""

from __future__ import annotations

import pytest

from pdf_autolink.config import Config
from pdf_autolink.sheetid import identify_all, identify_sheet
from tests.helpers.pagetext import page, title, word

CFG = Config()
# Vùng khung tên mặc định trên trang 612x792: x >= 336.6 và y >= 554.4


@pytest.mark.parametrize("code", ["A101", "M201", "S-101", "E0.01"])
def test_identify_sheet_recognises_common_codes(code):
    assert identify_sheet(title(code), CFG) == code


def test_lowercase_code_is_not_a_sheet_code():
    assert identify_sheet(page([word("a101", 500, 740, 24)]), CFG) is None


def test_page_without_code_returns_none():
    p = page([word("NOTES", 500, 740, 24), word("1:100", 400, 700, 12)])
    assert identify_sheet(p, CFG) is None


def test_empty_page_returns_none():
    assert identify_sheet(page([]), CFG) is None


def test_large_code_outside_title_block_is_ignored():
    p = page([word("Z999", 50, 50, 60), word("A101", 500, 740, 24)])
    assert identify_sheet(p, CFG) == "A101"


def test_only_code_outside_title_block_gives_none():
    assert identify_sheet(page([word("A101", 50, 50, 40)]), CFG) is None


def test_word_centre_decides_membership_of_region():
    # tâm nằm trong vùng dù x0 nằm ngoài (x0=330 < 336.6, rộng 52.8 -> tâm 356.4)
    inside = page([word("A101", 330, 740, 24)])
    assert identify_sheet(inside, CFG) == "A101"
    # x1 nằm trong vùng nhưng tâm ở ngoài (x0=300 -> tâm 326.4 < 336.6)
    outside = page([word("A101", 300, 740, 24)])
    assert identify_sheet(outside, CFG) is None


def test_non_matching_words_in_title_block_are_skipped():
    p = page(
        [
            word("SCALE", 400, 600, 30),
            word("A101-REV", 400, 650, 30),
            word("A101", 500, 740, 12),
        ]
    )
    assert identify_sheet(p, CFG) == "A101"


def test_multiple_candidates_pick_largest_font():
    p = page([word("A102", 500, 600, 10), word("A101", 500, 700, 24), word("A103", 500, 740, 12)])
    assert identify_sheet(p, CFG) == "A101"


def test_tie_on_size_prefers_lowest_on_page():
    p = page([word("A102", 500, 600, 20), word("A101", 500, 740, 20)])
    assert identify_sheet(p, CFG) == "A101"


def test_tie_on_size_and_height_prefers_rightmost():
    p = page([word("A102", 400, 740, 20), word("A101", 500, 740, 20)])
    assert identify_sheet(p, CFG) == "A101"


def test_custom_region_and_regex_are_honoured():
    cfg = Config(title_block_region=(0.0, 0.0, 0.5, 0.2), sheet_regex=r"DWG-\d{3}")
    p = page([word("DWG-007", 50, 30, 20), word("A101", 500, 740, 24)])
    assert identify_sheet(p, cfg) == "DWG-007"


def test_identify_all_builds_index():
    pages = [title("A101", index=0), title("A102", index=1), page([], index=2)]
    idx = identify_all(pages, CFG)
    assert idx.by_code == {"A101": [0], "A102": [1]}
    assert idx.unrecognized == [2]
    assert idx.page_codes == {0: "A101", 1: "A102", 2: None}


def test_identify_all_duplicate_code_lists_all_pages_in_order():
    pages = [title("A101", index=0), title("A101", index=1), title("A102", index=2)]
    idx = identify_all(pages, CFG)
    assert idx.by_code["A101"] == [0, 1]
    assert idx.by_code["A102"] == [2]
    assert idx.unrecognized == []


def test_identify_all_dash_variant_is_a_different_code():
    idx = identify_all([title("A-501", index=0), title("A501", index=1)], CFG)
    assert idx.by_code == {"A-501": [0], "A501": [1]}


def test_identify_all_empty_input():
    idx = identify_all([], CFG)
    assert idx.by_code == {}
    assert idx.unrecognized == []
    assert idx.page_codes == {}
