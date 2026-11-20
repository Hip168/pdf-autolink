"""[1-3] add_links: cấu trúc annotation, giữ cái cũ, idempotent, toạ độ."""

from __future__ import annotations

import pikepdf
import pytest
from pdf_autolink.annotate import add_links

from pdf_autolink.config import Config
from pdf_autolink.models import Reference, RefKind, Resolved, Status
from tests.helpers.make_pdf import PageSpec, build, count_links, links
from tests.helpers.pagetext import page

CFG = Config()
DISPLAY_RECT = (100.0, 200.0, 150.0, 210.0)
PDF_RECT = (100, 582, 150, 592)  # hằng số tính tay cho trang 612x792, Rotate 0


def _ref(rect=DISPLAY_RECT, source=0, code="A102") -> Reference:
    return Reference(source, code, RefKind.SHEET, code, rect)


def _linked(target: int, rect=DISPLAY_RECT, source=0) -> Resolved:
    return Resolved(_ref(rect, source), Status.LINKED, target)


def _make(tmp_path, specs=None):
    specs = specs or [PageSpec("A101"), PageSpec("A102"), PageSpec("A103")]
    return build(specs, tmp_path / "in.pdf")


def _pages(n=3):
    return [page([], index=i) for i in range(n)]


def test_link_structure_matches_contract(tmp_path):
    with pikepdf.open(_make(tmp_path)) as pdf:
        added, skipped = add_links(pdf, [_linked(1)], _pages(), CFG)
        assert (added, skipped) == (1, 0)
        annots = pdf.pages[0].obj["/Annots"]
        assert len(annots) == 1
        a = annots[0]
        assert str(a["/Subtype"]) == "/Link"
        assert str(a.get("/Type", "/Annot")) == "/Annot"
        assert [float(v) for v in a["/Border"]] == [0, 0, 0]
        assert str(a["/A"]["/S"]) == "/GoTo"
        dest = a["/A"]["/D"]
        assert dest[0].objgen == pdf.pages[1].obj.objgen
        assert str(dest[1]) == "/Fit"
        assert "/URI" not in a["/A"]


def test_rect_matches_hand_computed_pdf_coordinates(tmp_path):
    with pikepdf.open(_make(tmp_path)) as pdf:
        add_links(pdf, [_linked(1)], _pages(), CFG)
        ((rect, target, _),) = links(pdf, 0)
    assert target == 1
    assert rect == pytest.approx(PDF_RECT, abs=2.0)


def test_rect_on_rotated_page_is_unrotated(tmp_path):
    specs = [PageSpec("A101", rotate=90), PageSpec("A102")]
    pages = [page([], index=0, width=792, height=612), page([], index=1)]
    with pikepdf.open(_make(tmp_path, specs)) as pdf:
        add_links(pdf, [_linked(1)], pages, CFG)
        ((rect, _, _),) = links(pdf, 0)
    # Rotate 90, CropBox = MediaBox: hộp hiển thị (100,200,150,210) -> (200,100,210,150)
    assert rect == pytest.approx((200, 100, 210, 150), abs=2.0)


def test_rect_on_page_with_offset_cropbox(tmp_path):
    specs = [PageSpec("A101", cropbox=(20, 30, 500, 700)), PageSpec("A102")]
    pages = [page([], index=0, width=480, height=670), page([], index=1)]
    with pikepdf.open(_make(tmp_path, specs)) as pdf:
        add_links(pdf, [_linked(1)], pages, CFG)
        ((rect, _, _),) = links(pdf, 0)
    assert rect == pytest.approx((120, 490, 170, 500), abs=2.0)


@pytest.mark.parametrize("status", [Status.UNMATCHED, Status.AMBIGUOUS])
def test_unresolved_references_get_no_link(tmp_path, status):
    res = Resolved(_ref(), status, None)
    with pikepdf.open(_make(tmp_path)) as pdf:
        assert add_links(pdf, [res], _pages(), CFG) == (0, 0)
        assert count_links(pdf) == 0


def test_links_are_added_to_their_own_source_pages(tmp_path):
    resolved = [_linked(1, source=0), _linked(0, source=2), _linked(1, source=2)]
    with pikepdf.open(_make(tmp_path)) as pdf:
        added, _ = add_links(pdf, resolved, _pages(), CFG)
        assert added == 3
        assert len(links(pdf, 0)) == 1
        assert len(links(pdf, 1)) == 0
        assert len(links(pdf, 2)) == 2


def _add_existing_annots(pdf, indirect: bool):
    page0 = pdf.pages[0].obj
    uri = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Annot,
            Subtype=pikepdf.Name.Link,
            Rect=[10, 10, 60, 30],
            Border=[0, 0, 0],
            A=pikepdf.Dictionary(S=pikepdf.Name.URI, URI=pikepdf.String("https://example.com")),
        )
    )
    note = pdf.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Annot,
            Subtype=pikepdf.Name.Text,
            Rect=[300, 300, 320, 320],
            Contents=pikepdf.String("hello"),
        )
    )
    arr = pikepdf.Array([uri, note])
    page0["/Annots"] = pdf.make_indirect(arr) if indirect else arr


@pytest.mark.parametrize("indirect", [False, True])
def test_existing_annotations_are_preserved(tmp_path, indirect):
    with pikepdf.open(_make(tmp_path)) as pdf:
        _add_existing_annots(pdf, indirect)
        added, _ = add_links(pdf, [_linked(1)], _pages(), CFG)
        assert added == 1
        annots = list(pdf.pages[0].obj["/Annots"])
        assert len(annots) == 3
        subtypes = sorted(str(a["/Subtype"]) for a in annots)
        assert subtypes == ["/Link", "/Link", "/Text"]
        uris = [a for a in annots if "/URI" in a.get("/A", {})]
        assert len(uris) == 1
        assert str(uris[0]["/A"]["/URI"]) == "https://example.com"
        texts = [a for a in annots if str(a["/Subtype"]) == "/Text"]
        assert str(texts[0]["/Contents"]) == "hello"


def test_page_content_stream_is_untouched(tmp_path):
    with pikepdf.open(_make(tmp_path)) as pdf:
        before = pdf.pages[0].obj["/Contents"].read_bytes()
        add_links(pdf, [_linked(1)], _pages(), CFG)
        after = pdf.pages[0].obj["/Contents"].read_bytes()
    assert before == after


def test_running_twice_is_idempotent(tmp_path):
    out = tmp_path / "out.pdf"
    resolved = [_linked(1), _linked(2, rect=(100.0, 300.0, 150.0, 310.0))]
    with pikepdf.open(_make(tmp_path)) as pdf:
        assert add_links(pdf, resolved, _pages(), CFG) == (2, 0)
        pdf.save(out)
    with pikepdf.open(out) as pdf:
        assert count_links(pdf) == 2
        assert add_links(pdf, resolved, _pages(), CFG) == (0, 2)
        assert count_links(pdf) == 2


def test_same_call_twice_in_memory_does_not_duplicate(tmp_path):
    with pikepdf.open(_make(tmp_path)) as pdf:
        add_links(pdf, [_linked(1)], _pages(), CFG)
        added, skipped = add_links(pdf, [_linked(1)], _pages(), CFG)
        assert (added, skipped) == (0, 1)
        assert count_links(pdf) == 1


def test_slightly_shifted_existing_link_counts_as_duplicate(tmp_path):
    shifted = (101.0, 200.5, 151.0, 210.5)  # IoU > 0.9 với hộp gốc
    with pikepdf.open(_make(tmp_path)) as pdf:
        add_links(pdf, [_linked(1, rect=shifted)], _pages(), CFG)
        added, skipped = add_links(pdf, [_linked(1)], _pages(), CFG)
        assert (added, skipped) == (0, 1)
        assert count_links(pdf) == 1


def test_same_rect_but_different_target_is_not_duplicate(tmp_path):
    with pikepdf.open(_make(tmp_path)) as pdf:
        add_links(pdf, [_linked(1)], _pages(), CFG)
        added, skipped = add_links(pdf, [_linked(2)], _pages(), CFG)
        assert (added, skipped) == (1, 0)
        assert count_links(pdf) == 2


def test_same_target_but_far_rect_is_not_duplicate(tmp_path):
    far = (100.0, 400.0, 150.0, 410.0)
    with pikepdf.open(_make(tmp_path)) as pdf:
        add_links(pdf, [_linked(1)], _pages(), CFG)
        added, skipped = add_links(pdf, [_linked(1, rect=far)], _pages(), CFG)
        assert (added, skipped) == (1, 0)


def test_saved_file_reopens_without_error(tmp_path):
    out = tmp_path / "out.pdf"
    with pikepdf.open(_make(tmp_path)) as pdf:
        _add_existing_annots(pdf, indirect=False)
        add_links(pdf, [_linked(1), _linked(2)], _pages(), CFG)
        pdf.save(out)
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 3
        assert count_links(pdf) == 2  # chỉ đếm GoTo; link URI cũ không tính
        assert len(pdf.pages[0].obj["/Annots"]) == 4  # 2 cũ + 2 mới
