"""[1-1] PdfplumberSource.pages(): toạ độ hiển thị, kích thước, cỡ chữ."""

from __future__ import annotations

import pytest

from pdf_autolink.textsource import PdfplumberSource
from tests.helpers.make_pdf import PageSpec, build

CROP = (20.0, 30.0, 500.0, 700.0)  # rộng 480, cao 670
SCENARIOS = [
    # (rotate, cropbox, display width, display height)
    (0, None, 612, 792),
    (90, None, 792, 612),
    (180, None, 612, 792),
    (270, None, 792, 612),
    (0, CROP, 480, 670),
    (90, CROP, 670, 480),
    (180, CROP, 480, 670),
    (270, CROP, 670, 480),
]


def _read(tmp_path, spec):
    pdf = build([spec], tmp_path / "in.pdf")
    return list(PdfplumberSource(pdf).pages())


@pytest.mark.parametrize(("rotate", "crop", "w", "h"), SCENARIOS)
def test_page_size_is_display_size_after_rotate_and_cropbox(tmp_path, rotate, crop, w, h):
    (page,) = _read(tmp_path, PageSpec("A101", rotate=rotate, cropbox=crop))
    assert page.width == pytest.approx(w, abs=1)
    assert page.height == pytest.approx(h, abs=1)


@pytest.mark.parametrize(("rotate", "crop", "w", "h"), SCENARIOS)
def test_word_box_is_at_known_display_position(tmp_path, rotate, crop, w, h):
    spec = PageSpec("A101", texts=[(100, 200, 10, "HELLO")], rotate=rotate, cropbox=crop)
    (page,) = _read(tmp_path, spec)
    hello = [b for b in page.words if b.text == "HELLO"]
    assert len(hello) == 1
    b = hello[0]
    assert b.x0 == pytest.approx(100, abs=2)
    assert 188 <= b.y0 <= 197  # đỉnh chữ ngay phía trên đường cơ sở y=200
    assert 199 <= b.y1 <= 207  # đáy chữ ngay dưới đường cơ sở
    assert 20 <= b.x1 - b.x0 <= 40  # "HELLO" cỡ 10 ~ 33pt
    assert b.size == pytest.approx(10, abs=0.6)


@pytest.mark.parametrize(("rotate", "crop", "w", "h"), SCENARIOS)
def test_sheet_code_lands_in_bottom_right_of_display(tmp_path, rotate, crop, w, h):
    (page,) = _read(tmp_path, PageSpec("A101", rotate=rotate, cropbox=crop))
    code = [b for b in page.words if b.text == "A101"]
    assert len(code) == 1
    b = code[0]
    assert b.size == pytest.approx(24, abs=1)
    assert b.x0 > 0.55 * w
    assert b.y0 > 0.70 * h
    assert b.x1 <= w + 1
    assert b.y1 <= h + 1


def test_pages_are_zero_based_and_in_order(tmp_path):
    pdf = build([PageSpec("A101"), PageSpec("A102"), PageSpec("A103")], tmp_path / "in.pdf")
    pages = list(PdfplumberSource(pdf).pages())
    assert [p.index for p in pages] == [0, 1, 2]
    assert [[b.text for b in p.words] for p in pages] == [["A101"], ["A102"], ["A103"]]


def test_mixed_page_sizes_report_their_own_size(tmp_path):
    pdf = build(
        [PageSpec("A101", size=(612, 792)), PageSpec("A102", size=(1224, 792))],
        tmp_path / "in.pdf",
    )
    p0, p1 = PdfplumberSource(pdf).pages()
    assert p0.width == pytest.approx(612, abs=1)
    assert p1.width == pytest.approx(1224, abs=1)


def test_accepts_str_path_and_blank_page_has_no_words(tmp_path):
    pdf = build([PageSpec(None)], tmp_path / "in.pdf")
    (page,) = PdfplumberSource(str(pdf)).pages()
    assert page.words == []
