"""[1-1] display_to_pdf_rect: Rotate 0/90/180/270 x CropBox lệch gốc.

Giá trị kỳ vọng là hằng số tính tay (không gọi lại công thức của code):
hiển thị gốc trên-trái, tương đối mép CropBox -> user space PDF gốc dưới-trái.
Hộp mẫu hiển thị: (100, 200, 150, 210).
"""

from __future__ import annotations

import pytest

from pdf_autolink.geometry import display_to_pdf_rect

DISPLAY = (100.0, 200.0, 150.0, 210.0)
FULL = (0.0, 0.0, 612.0, 792.0)
OFFSET = (20.0, 30.0, 500.0, 700.0)  # rộng 480, cao 670

CASES = [
    # (cropbox, rotate, expected pdf rect)
    (FULL, 0, (100, 582, 150, 592)),
    (OFFSET, 0, (120, 490, 170, 500)),
    (FULL, 90, (200, 100, 210, 150)),
    (OFFSET, 90, (220, 130, 230, 180)),
    (FULL, 180, (462, 200, 512, 210)),
    (OFFSET, 180, (350, 230, 400, 240)),
    (FULL, 270, (402, 642, 412, 692)),
    (OFFSET, 270, (290, 550, 300, 600)),
]


@pytest.mark.parametrize(("cropbox", "rotate", "expected"), CASES)
def test_display_rect_maps_to_expected_pdf_rect(cropbox, rotate, expected):
    got = display_to_pdf_rect(DISPLAY, cropbox=cropbox, rotate=rotate)
    assert got == pytest.approx(expected, abs=2.0)


@pytest.mark.parametrize(("cropbox", "rotate", "expected"), CASES)
def test_result_is_normalised_x0_lt_x1_and_y0_lt_y1(cropbox, rotate, expected):
    x0, y0, x1, y1 = display_to_pdf_rect(DISPLAY, cropbox=cropbox, rotate=rotate)
    assert x0 < x1
    assert y0 < y1


def test_rotate_90_swaps_extent_of_the_box():
    # hộp ngang 50x10 trên hiển thị -> sau gỡ xoay 90 thành 10 rộng x 50 cao
    x0, y0, x1, y1 = display_to_pdf_rect(DISPLAY, cropbox=FULL, rotate=90)
    assert (x1 - x0) == pytest.approx(10, abs=1)
    assert (y1 - y0) == pytest.approx(50, abs=1)


def test_rotate_0_keeps_extent_of_the_box():
    x0, y0, x1, y1 = display_to_pdf_rect(DISPLAY, cropbox=OFFSET, rotate=0)
    assert (x1 - x0) == pytest.approx(50, abs=1)
    assert (y1 - y0) == pytest.approx(10, abs=1)
