"""[1-3] autolink() end-to-end trên bộ 5 trang + lỗi đầu vào."""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterator

import pikepdf
import pytest

from pdf_autolink import PdfAutolinkError, autolink
from pdf_autolink.models import PageText, Status, WordBox
from tests.helpers.make_pdf import PageSpec, build, count_links, links

# Vị trí PDF kỳ vọng tính tay (trang 612x792 Rotate 0: y_pdf = 792 - y_hiển_thị).


def _covers(rect, point, pad=2.0):
    x0, y0, x1, y1 = rect
    return x0 - pad <= point[0] <= x1 + pad and y0 - pad <= point[1] <= y1 + pad


def _five_pages():
    return [
        PageSpec(
            "A001",
            texts=[(100, 200, 10, "A101"), (100, 230, 10, "A102"), (100, 260, 10, "A103")],
        ),
        PageSpec("A101", texts=[(200, 300, 10, "3/A103")]),
        PageSpec("A102", texts=[(300, 400, 10, "3"), (300, 412, 10, "A103")]),
        PageSpec("A103", texts=[(150, 250, 10, "A101")], rotate=90),
        PageSpec(None, texts=[(100, 100, 10, "A999")]),
    ]


@pytest.fixture
def five(tmp_path):
    src = build(_five_pages(), tmp_path / "plans.pdf")
    out = tmp_path / "plans_out.pdf"
    rep = tmp_path / "plans_out.csv"
    result = autolink(src, out, rep)
    return src, out, rep, result


def test_result_counts_and_index(five):
    _, _, _, result = five
    assert result.links_added == 6
    assert result.links_skipped_existing == 0
    assert result.sheets.by_code == {
        "A001": [0],
        "A101": [1],
        "A102": [2],
        "A103": [3],
    }
    assert result.sheets.unrecognized == [4]
    statuses = sorted(r.status for r in result.resolved)
    assert statuses == sorted([Status.LINKED] * 6 + [Status.UNMATCHED])


def test_table_of_contents_links_point_to_right_pages(five):
    _, out, _, _ = five
    with pikepdf.open(out) as pdf:
        found = links(pdf, 0)
    assert len(found) == 3
    by_target = {t: r for r, t, _ in found}
    assert sorted(by_target) == [1, 2, 3]
    # baseline hiển thị y=200/230/260 -> PDF y=592/562/532; chữ bắt đầu x=100
    assert _covers(by_target[1], (103, 592))
    assert _covers(by_target[2], (103, 562))
    assert _covers(by_target[3], (103, 532))
    for rect in by_target.values():
        assert rect[2] - rect[0] < 40
        assert rect[3] - rect[1] < 20


def test_one_line_detail_bubble_links_whole_bubble_to_its_sheet(five):
    _, out, _, _ = five
    with pikepdf.open(out) as pdf:
        found = links(pdf, 1)
    assert len(found) == 1  # không thêm link SHEET trùng, không link cho mã của chính trang
    rect, target, _ = found[0]
    assert target == 3
    assert _covers(rect, (203, 492))  # đầu "3/A103"
    assert _covers(rect, (225, 492))  # cuối "3/A103" (rộng ~33pt)


def test_two_line_detail_bubble_is_one_link_covering_both_lines(five):
    _, out, _, _ = five
    with pikepdf.open(out) as pdf:
        found = links(pdf, 2)
    assert len(found) == 1
    rect, target, _ = found[0]
    assert target == 3
    assert _covers(rect, (301, 392))  # dòng "3" (baseline hiển thị 400)
    assert _covers(rect, (301, 380))  # dòng "A103" (baseline hiển thị 412)


def test_rotated_page_link_is_in_unrotated_user_space(five):
    _, out, _, _ = five
    with pikepdf.open(out) as pdf:
        found = links(pdf, 3)
    assert len(found) == 1
    rect, target, _ = found[0]
    assert target == 1
    # Rotate 90: chữ "A101" ở hiển thị (150,250) -> user space (250,150),
    # chiếm x 242..250 (cao 10), y 150..173 (rộng ~23).
    assert _covers(rect, (246, 160))
    assert _covers(rect, (246, 170))
    assert 6 <= rect[2] - rect[0] <= 18
    assert 18 <= rect[3] - rect[1] <= 32


def test_unmatched_reference_and_unrecognized_page_get_no_link(five):
    _, out, _, _ = five
    with pikepdf.open(out) as pdf:
        assert links(pdf, 4) == []
        assert count_links(pdf) == 6


def test_output_has_all_pages_and_input_is_unchanged(tmp_path):
    src = build(_five_pages(), tmp_path / "plans.pdf")
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    out = tmp_path / "o.pdf"
    autolink(src, out, tmp_path / "o.csv")
    assert hashlib.sha256(src.read_bytes()).hexdigest() == before
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 5


def test_csv_report_is_written_with_expected_rows(five):
    _, _, rep, _ = five
    with open(rep, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == [
        "source_page",
        "text",
        "kind",
        "target_page",
        "status",
        "note",
    ]
    linked = [
        (r["source_page"], r["text"], r["target_page"]) for r in rows if r["status"] == "linked"
    ]
    assert sorted(linked) == sorted(
        [
            ("1", "A101", "2"),
            ("1", "A102", "3"),
            ("1", "A103", "4"),
            ("2", "3/A103", "4"),
            ("3", "3/A103", "4"),
            ("4", "A101", "2"),
        ]
    )
    unmatched = [r for r in rows if r["status"] == "unmatched"]
    real = [r for r in unmatched if r["note"] != "sheet id not recognized"]
    assert {r["text"] for r in real} == {"A999"}
    assert [r["source_page"] for r in real] == ["5"]
    notes = [r for r in rows if r["note"] == "sheet id not recognized"]
    assert [r["source_page"] for r in notes] == ["5"]


def test_running_again_on_output_adds_no_duplicate_links(five, tmp_path):
    _, out, _, _ = five
    again = tmp_path / "again.pdf"
    result = autolink(out, again, tmp_path / "again.csv")
    assert result.links_added == 0
    assert result.links_skipped_existing == 6
    with pikepdf.open(again) as pdf:
        assert count_links(pdf) == 6


def test_existing_annotations_survive_the_pipeline(tmp_path):
    src = build(_five_pages(), tmp_path / "plans.pdf")
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        pdf.pages[0].obj["/Annots"] = pikepdf.Array(
            [
                pdf.make_indirect(
                    pikepdf.Dictionary(
                        Type=pikepdf.Name.Annot,
                        Subtype=pikepdf.Name.Link,
                        Rect=[10, 10, 60, 30],
                        A=pikepdf.Dictionary(
                            S=pikepdf.Name.URI, URI=pikepdf.String("https://example.com")
                        ),
                    )
                )
            ]
        )
        pdf.save(src)
    out = tmp_path / "o.pdf"
    autolink(src, out, tmp_path / "o.csv")
    with pikepdf.open(out) as pdf:
        annots = list(pdf.pages[0].obj["/Annots"])
        assert len(annots) == 4
        assert sum("/URI" in a.get("/A", {}) for a in annots) == 1


class _FakeSource:
    """TextSource giả: 2 trang trắng, mã + tham chiếu do nguồn cung cấp."""

    def pages(self) -> Iterator[PageText]:
        def w(text, x, y, size):
            return WordBox(text, x, y, x + 0.55 * size * len(text), y + size, size)

        yield PageText(0, 612, 792, [w("A101", 500, 740, 24), w("A102", 100, 100, 10)])
        yield PageText(1, 612, 792, [w("A102", 500, 740, 24)])


def test_custom_text_source_is_used_instead_of_reading_pdf_text(tmp_path):
    src = build([PageSpec(None), PageSpec(None)], tmp_path / "blank.pdf")
    out = tmp_path / "o.pdf"
    result = autolink(src, out, tmp_path / "o.csv", source=_FakeSource())
    assert result.sheets.by_code == {"A101": [0], "A102": [1]}
    assert result.links_added == 1
    with pikepdf.open(out) as pdf:
        ((rect, target, _),) = links(pdf, 0)
    assert target == 1
    # hộp hiển thị (100,100)-(~123,110) -> PDF y 682..692
    assert _covers(rect, (105, 687), pad=1.0)
    assert rect[3] - rect[1] < 20


def test_report_none_writes_no_csv(tmp_path):
    src = build(_five_pages(), tmp_path / "plans.pdf")
    out = tmp_path / "o.pdf"
    autolink(src, out)
    assert out.is_file()
    assert list(tmp_path.glob("*.csv")) == []


def test_self_reference_gets_no_link_in_pipeline(tmp_path):
    src = build([PageSpec("A101", texts=[(100, 200, 10, "A101")])], tmp_path / "s.pdf")
    result = autolink(src, tmp_path / "o.pdf", tmp_path / "o.csv")
    assert [r.status for r in result.resolved] == [Status.SELF]
    assert result.links_added == 0
    with pikepdf.open(tmp_path / "o.pdf") as pdf:
        assert count_links(pdf) == 0


def test_missing_input_raises(tmp_path):
    with pytest.raises(PdfAutolinkError):
        autolink(tmp_path / "nope.pdf", tmp_path / "o.pdf")


def test_non_pdf_input_raises(tmp_path):
    bad = tmp_path / "x.pdf"
    bad.write_text("this is not a pdf")
    with pytest.raises(PdfAutolinkError):
        autolink(bad, tmp_path / "o.pdf")


def test_encrypted_input_raises(tmp_path):
    src = build([PageSpec("A101")], tmp_path / "plain.pdf")
    enc = tmp_path / "enc.pdf"
    with pikepdf.open(src) as pdf:
        pdf.save(enc, encryption=pikepdf.Encryption(owner="o", user="u"))
    with pytest.raises(PdfAutolinkError):
        autolink(enc, tmp_path / "o.pdf")


def test_zero_page_input_raises(tmp_path):
    empty = tmp_path / "empty.pdf"
    pdf = pikepdf.Pdf.new()
    pdf.save(empty)
    with pytest.raises(PdfAutolinkError):
        autolink(empty, tmp_path / "o.pdf")


def test_output_equal_to_input_raises_and_leaves_input_intact(tmp_path):
    src = build(_five_pages(), tmp_path / "plans.pdf")
    before = src.read_bytes()
    with pytest.raises(PdfAutolinkError):
        autolink(src, src, tmp_path / "o.csv")
    assert src.read_bytes() == before


@pytest.mark.parametrize(
    ("rotate", "crop", "point", "w_range", "h_range"),
    [
        # hộp hiển thị ~ (100,192)-(123,202); điểm kỳ vọng tính tay trong user space
        (180, None, (500, 197), (18, 28), (6, 14)),
        (270, None, (415, 680), (6, 14), (18, 28)),
        (0, (20, 30, 500, 700), (130, 503), (18, 28), (6, 14)),
        (90, (20, 30, 500, 700), (217, 140), (6, 14), (18, 28)),
    ],
)
def test_e2e_link_position_for_rotate_180_270_and_offset_cropbox(
    tmp_path, rotate, crop, point, w_range, h_range
):
    specs = [
        PageSpec("A101", texts=[(100, 200, 10, "A102")], rotate=rotate, cropbox=crop),
        PageSpec("A102"),
    ]
    src = build(specs, tmp_path / "p.pdf")
    out = tmp_path / "o.pdf"
    result = autolink(src, out, tmp_path / "o.csv")
    assert result.links_added == 1
    with pikepdf.open(out) as pdf:
        ((rect, target, _),) = links(pdf, 0)
    assert target == 1
    assert _covers(rect, point, pad=1.0)
    assert w_range[0] <= rect[2] - rect[0] <= w_range[1]
    assert h_range[0] <= rect[3] - rect[1] <= h_range[1]
