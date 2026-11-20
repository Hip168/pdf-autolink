"""[1-2] find_references: mã trang, bong bóng chi tiết 1 / 2 dòng."""

from __future__ import annotations

from pdf_autolink.config import Config
from pdf_autolink.models import Reference, RefKind
from pdf_autolink.refs import find_references
from tests.helpers.pagetext import page, word

CFG = Config()


def _key(r: Reference):
    return (r.text.replace(" ", ""), r.kind, r.code)


def _union(*boxes):
    return (
        min(b.x0 for b in boxes),
        min(b.y0 for b in boxes),
        max(b.x1 for b in boxes),
        max(b.y1 for b in boxes),
    )


def test_table_of_contents_gives_one_sheet_reference_per_code():
    ws = [word("A101", 100, 100), word("A102", 100, 120), word("M201", 100, 140)]
    refs = find_references(page(ws), None, CFG)
    assert sorted(_key(r) for r in refs) == [
        ("A101", RefKind.SHEET, "A101"),
        ("A102", RefKind.SHEET, "A102"),
        ("M201", RefKind.SHEET, "M201"),
    ]
    by_text = {r.text: r for r in refs}
    for w in ws:
        assert by_text[w.text].rect == (w.x0, w.y0, w.x1, w.y1)
        assert by_text[w.text].page == 0


def test_reference_page_is_zero_based_source_index():
    refs = find_references(page([word("A101", 100, 100)], index=4), None, CFG)
    assert [r.page for r in refs] == [4]


def test_code_is_normalised_and_dash_is_kept():
    refs = find_references(page([word("S-101", 100, 100)]), None, CFG)
    assert [(r.text, r.code) for r in refs] == [("S-101", "S-101")]


def test_non_code_words_produce_nothing():
    ws = [word("NOTE", 100, 100), word("1:100", 100, 120), word("3", 100, 140)]
    assert find_references(page(ws), None, CFG) == []


def test_own_code_in_title_block_is_not_emitted():
    ws = [word("A101", 500, 740, 24), word("A102", 100, 100)]
    refs = find_references(page(ws), "A101", CFG)
    assert [r.code for r in refs] == ["A102"]


def test_own_code_elsewhere_on_page_is_still_emitted():
    ws = [word("A101", 500, 740, 24), word("A101", 100, 100)]
    refs = find_references(page(ws), "A101", CFG)
    assert len(refs) == 1
    assert refs[0].code == "A101"
    assert refs[0].rect[0] == 100


def test_other_code_inside_title_block_area_is_still_emitted():
    ws = [word("A101", 500, 740, 24), word("A102", 400, 600, 10)]
    refs = find_references(page(ws), "A101", CFG)
    assert [r.code for r in refs] == ["A102"]


def test_detail_one_line_single_word():
    w = word("3/A501", 200, 300)
    refs = find_references(page([w]), None, CFG)
    assert len(refs) == 1
    r = refs[0]
    assert (r.text, r.kind, r.code) == ("3/A501", RefKind.DETAIL, "A501")
    assert r.rect == (w.x0, w.y0, w.x1, w.y1)


def test_detail_one_line_with_dashed_code():
    refs = find_references(page([word("12/S-101", 200, 300)]), None, CFG)
    assert [(r.kind, r.code) for r in refs] == [(RefKind.DETAIL, "S-101")]


def test_detail_one_line_split_in_adjacent_words_same_line():
    a, b, c = word("3", 200, 300), word("/", 207, 300), word("A501", 214, 300)
    refs = find_references(page([a, b, c]), None, CFG)
    assert len(refs) == 1
    r = refs[0]
    assert (r.kind, r.code) == (RefKind.DETAIL, "A501")
    assert r.text.replace(" ", "") == "3/A501"
    assert r.rect == _union(a, b, c)


def test_detail_two_lines_stacked():
    top, bottom = word("3", 300, 400), word("A501", 300, 412)
    refs = find_references(page([top, bottom]), None, CFG)
    assert len(refs) == 1
    r = refs[0]
    assert (r.text, r.kind, r.code) == ("3/A501", RefKind.DETAIL, "A501")
    assert r.rect == _union(top, bottom)


def test_detail_two_lines_does_not_also_emit_sheet_reference():
    refs = find_references(page([word("3", 300, 400), word("A501", 300, 412)]), None, CFG)
    assert [r.kind for r in refs] == [RefKind.DETAIL]


def test_detail_two_lines_gap_just_under_threshold_is_detail():
    # cỡ 10, ngưỡng 1.5*10 = 15; khoảng cách dọc giữa hai hộp = 14
    refs = find_references(page([word("3", 300, 400), word("A501", 300, 424)]), None, CFG)
    assert [r.kind for r in refs] == [RefKind.DETAIL]


def test_two_lines_farther_than_threshold_gives_only_sheet():
    # khoảng cách dọc 30 > 15
    refs = find_references(page([word("3", 300, 400), word("A501", 300, 440)]), None, CFG)
    assert [(r.text, r.kind, r.code) for r in refs] == [("A501", RefKind.SHEET, "A501")]


def test_two_lines_threshold_follows_config_factor():
    ws = [word("3", 300, 400), word("A501", 300, 440)]  # gap 30 = 3 * cỡ
    refs = find_references(page(ws), None, Config(stack_max_gap_factor=4.0))
    assert [r.kind for r in refs] == [RefKind.DETAIL]


def test_two_lines_horizontally_far_apart_is_not_detail():
    ws = [word("3", 100, 400), word("A501", 400, 412)]
    refs = find_references(page(ws), None, CFG)
    assert [(r.kind, r.code) for r in refs] == [(RefKind.SHEET, "A501")]


def test_two_lines_offset_centres_within_two_font_sizes_is_detail():
    # "3" x 300..305.5 (tâm 302.75); "A501" x 307..329 (tâm 318): không chồng ngang,
    # lệch tâm ~15.3 <= 2*10
    ws = [word("3", 300, 400), word("A501", 307, 412)]
    refs = find_references(page(ws), None, CFG)
    assert [r.kind for r in refs] == [RefKind.DETAIL]


def test_upper_word_must_be_one_to_three_digits():
    ws = [word("1234", 300, 400), word("A501", 300, 412)]
    refs = find_references(page(ws), None, CFG)
    assert [(r.kind, r.code) for r in refs] == [(RefKind.SHEET, "A501")]


def test_upper_word_below_the_code_does_not_form_detail():
    ws = [word("A501", 300, 400), word("3", 300, 412)]
    refs = find_references(page(ws), None, CFG)
    assert [(r.kind, r.code) for r in refs] == [(RefKind.SHEET, "A501")]


def test_word_used_by_detail_is_not_reused_as_sheet():
    # "3" trên "A501" -> detail; "A502" ngay dưới A501 vẫn là SHEET riêng
    ws = [word("3", 300, 400), word("A501", 300, 412), word("A502", 300, 424)]
    refs = find_references(page(ws), None, CFG)
    assert sorted((r.kind, r.code) for r in refs) == [
        (RefKind.DETAIL, "A501"),
        (RefKind.SHEET, "A502"),
    ]


def test_mixed_page_toc_and_both_detail_styles():
    ws = [
        word("A102", 50, 100),
        word("2/A103", 200, 200),
        word("4", 300, 300),
        word("A104", 300, 312),
    ]
    refs = find_references(page(ws), "A101", CFG)
    assert sorted((r.text, r.kind, r.code) for r in refs) == [
        ("2/A103", RefKind.DETAIL, "A103"),
        ("4/A104", RefKind.DETAIL, "A104"),
        ("A102", RefKind.SHEET, "A102"),
    ]


def test_empty_page_has_no_references():
    assert find_references(page([]), "A101", CFG) == []
