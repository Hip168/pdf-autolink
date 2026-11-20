"""[1-3] Hành vi thêm sau review (D10).

Kiểm tra đường dẫn, ghi file an toàn, quyền, close, /Annots lạ.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator

import pdfplumber.page
import pikepdf
import pytest
from pdfminer.psexceptions import PSException

from pdf_autolink import PdfAutolinkError, autolink
from pdf_autolink.annotate import add_links
from pdf_autolink.cli import main
from pdf_autolink.config import Config
from pdf_autolink.models import PageText, Reference, RefKind, Resolved, Status
from tests.helpers.make_pdf import PageSpec, build
from tests.helpers.pagetext import page

needs_non_root = pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="quyền thư mục không có tác dụng với root / Windows",
)


def _src(tmp_path):
    return build(
        [
            PageSpec("A101", texts=[(100, 200, 10, "A102")]),
            PageSpec("A102", texts=[(100, 200, 10, "A101")]),
        ],
        tmp_path / "plans.pdf",
    )


# --- 1. report trùng input / output ---------------------------------------------------


def test_report_equal_to_input_raises_and_input_is_untouched(tmp_path):
    src = _src(tmp_path)
    before = src.read_bytes()
    with pytest.raises(PdfAutolinkError, match="report must be different from input and output"):
        autolink(src, tmp_path / "o.pdf", src)
    assert src.read_bytes() == before
    assert not (tmp_path / "o.pdf").exists()


def test_report_equal_to_output_raises_and_nothing_is_written(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "o.pdf"
    with pytest.raises(PdfAutolinkError, match="report must be different from input and output"):
        autolink(src, out, out)
    assert not out.exists()


def test_report_comparison_is_made_after_resolving_paths(tmp_path):
    src = _src(tmp_path)
    (tmp_path / "sub").mkdir()
    out = tmp_path / "o.pdf"
    spelled_differently = tmp_path / "sub" / ".." / "o.pdf"
    with pytest.raises(PdfAutolinkError, match="report must be different"):
        autolink(src, out, spelled_differently)
    assert not out.exists()


def test_cli_report_equal_to_input_exits_1_with_error_prefix(tmp_path, capsys):
    src = _src(tmp_path)
    before = src.read_bytes()
    assert main([str(src), "--report", str(src)]) == 1
    assert capsys.readouterr().err.startswith("pdf-autolink: error:")
    assert src.read_bytes() == before
    assert not (tmp_path / "plans_linked.pdf").exists()


# --- 2. thư mục ra / lỗi ghi ----------------------------------------------------------


def test_missing_output_directories_are_created_for_pdf_and_csv(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "out" / "sub" / "x.pdf"
    assert main([str(src), "-o", str(out)]) == 0
    assert out.is_file()
    assert (tmp_path / "out" / "sub" / "x.csv").is_file()


def test_autolink_creates_missing_report_directory(tmp_path):
    src = _src(tmp_path)
    rep = tmp_path / "r" / "deep" / "rep.csv"
    autolink(src, tmp_path / "o.pdf", rep)
    assert rep.is_file()


@needs_non_root
def test_read_only_output_directory_raises_cannot_write_and_leaves_no_temp(tmp_path):
    src = _src(tmp_path)
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        with pytest.raises(PdfAutolinkError, match="cannot write output"):
            autolink(src, ro / "o.pdf", tmp_path / "o.csv")
        assert list(ro.iterdir()) == []
    finally:
        ro.chmod(0o755)


@needs_non_root
def test_cli_read_only_output_directory_exits_1(tmp_path, capsys):
    src = _src(tmp_path)
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        assert main([str(src), "-o", str(ro / "o.pdf")]) == 1
        err = capsys.readouterr().err
        assert err.startswith("pdf-autolink: error:")
        assert "cannot write output" in err
        assert list(ro.iterdir()) == []
    finally:
        ro.chmod(0o755)


def test_unwritable_report_path_raises_cannot_write_report(tmp_path):
    src = _src(tmp_path)
    report_is_a_directory = tmp_path / "rep"
    report_is_a_directory.mkdir()
    with pytest.raises(PdfAutolinkError, match="cannot write report"):
        autolink(src, tmp_path / "o.pdf", report_is_a_directory)


class _BrokenSource:
    def pages(self) -> Iterator[PageText]:
        raise PSException("boom")
        yield  # pragma: no cover


def test_pdfminer_failure_becomes_cannot_read_text_error(tmp_path):
    src = _src(tmp_path)
    with pytest.raises(PdfAutolinkError, match="cannot read text from PDF"):
        autolink(src, tmp_path / "o.pdf", source=_BrokenSource())
    assert not (tmp_path / "o.pdf").exists()


# --- 3. quyền file ra ----------------------------------------------------------------


def test_output_pdf_permissions_follow_umask(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "o.pdf"
    old = os.umask(0o022)
    try:
        autolink(src, out)
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == 0o644


def test_output_pdf_permissions_with_stricter_umask(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "o.pdf"
    old = os.umask(0o077)
    try:
        autolink(src, out)
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600


# --- 4. page.close() ------------------------------------------------------------------


def test_text_source_closes_every_page(tmp_path, monkeypatch):
    from pdf_autolink.textsource import PdfplumberSource

    pdf = build([PageSpec("A101"), PageSpec("A102"), PageSpec("A103")], tmp_path / "in.pdf")
    closed: list[int] = []
    original = pdfplumber.page.Page.close

    def spy(self):
        closed.append(self.page_number)
        return original(self)

    monkeypatch.setattr(pdfplumber.page.Page, "close", spy)
    gen = PdfplumberSource(pdf).pages()
    # Khi nguồn trả trang i thì trang i đã được close
    # (tài liệu còn mở, chưa đóng hàng loạt).
    for expected in (1, 2, 3):
        got = next(gen)
        assert got.index == expected - 1
        assert expected in closed
    assert list(gen) == []


# --- 5. /Annots có phần tử lạ ---------------------------------------------------------


def test_odd_annots_entries_do_not_break_add_links(tmp_path):
    pdf_path = _src(tmp_path)
    ref = Reference(0, "A102", RefKind.SHEET, "A102", (100.0, 200.0, 150.0, 210.0))
    resolved = [Resolved(ref, Status.LINKED, 1)]
    with pikepdf.open(pdf_path) as pdf:
        pdf.pages[0].obj["/Annots"] = pikepdf.Array([None, 42, pikepdf.Name.Foo])
        added, skipped = add_links(pdf, resolved, [page([], 0), page([], 1)], Config())
        assert (added, skipped) == (1, 0)
        annots = pdf.pages[0].obj["/Annots"]
        assert len(annots) == 4  # 3 phần tử lạ giữ nguyên + 1 link mới
        link = annots[3]
        assert str(link["/Subtype"]) == "/Link"
        assert str(link["/A"]["/S"]) == "/GoTo"


def test_odd_annots_entries_survive_full_pipeline(tmp_path):
    src = _src(tmp_path)
    with pikepdf.open(src, allow_overwriting_input=True) as pdf:
        pdf.pages[0].obj["/Annots"] = pikepdf.Array([None, 42])
        pdf.save(src)
    out = tmp_path / "o.pdf"
    result = autolink(src, out)
    assert result.links_added == 2
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages[0].obj["/Annots"]) == 3
