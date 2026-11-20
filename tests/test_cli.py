"""[1-3] CLI pdf-autolink: đường dẫn mặc định, mã thoát, dòng tóm tắt."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pikepdf
import pytest
from pdf_autolink.cli import main

from tests.helpers.make_pdf import PageSpec, build, count_links


def _run(argv):
    """Gọi main(); sys.exit(2) của argparse cũng quy về mã thoát."""
    try:
        return main(argv)
    except SystemExit as exc:
        return exc.code


def _clean_pdf(tmp_path, name="plans.pdf"):
    """2 trang tham chiếu chéo, không có gì unmatched."""
    return build(
        [
            PageSpec("A101", texts=[(100, 200, 10, "A102")]),
            PageSpec("A102", texts=[(100, 200, 10, "A101")]),
        ],
        tmp_path / name,
    )


def _five_pdf(tmp_path):
    return build(
        [
            PageSpec(
                "A001",
                texts=[(100, 200, 10, "A101"), (100, 230, 10, "A102"), (100, 260, 10, "A103")],
            ),
            PageSpec("A101", texts=[(200, 300, 10, "3/A103")]),
            PageSpec("A102", texts=[(300, 400, 10, "3"), (300, 412, 10, "A103")]),
            PageSpec("A103", texts=[(150, 250, 10, "A101")], rotate=90),
            PageSpec(None, texts=[(100, 100, 10, "A999")]),
        ],
        tmp_path / "five.pdf",
    )


def test_default_output_and_report_are_next_to_input(tmp_path, capsys):
    src = _clean_pdf(tmp_path)
    assert _run([str(src)]) == 0
    out = tmp_path / "plans_linked.pdf"
    rep = tmp_path / "plans_linked.csv"
    assert out.is_file()
    assert rep.is_file()
    with pikepdf.open(out) as pdf:
        assert count_links(pdf) == 2


def test_last_stdout_line_is_exact_summary(tmp_path, capsys):
    src = _clean_pdf(tmp_path)
    assert _run([str(src)]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last == ("pdf-autolink: 2 pages, 2 links added, 0 existing, 0 unmatched, 0 ambiguous")


def test_exit_zero_even_when_there_are_unmatched(tmp_path, capsys):
    src = _five_pdf(tmp_path)
    assert _run([str(src)]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert re.fullmatch(
        r"pdf-autolink: 5 pages, 6 links added, 0 existing, \d+ unmatched, 0 ambiguous", last
    )


def test_second_run_reports_existing_links(tmp_path, capsys):
    src = _clean_pdf(tmp_path)
    assert _run([str(src)]) == 0
    capsys.readouterr()
    assert _run([str(tmp_path / "plans_linked.pdf"), "-o", str(tmp_path / "again.pdf")]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last == ("pdf-autolink: 2 pages, 0 links added, 2 existing, 0 unmatched, 0 ambiguous")


def test_explicit_output_and_report_paths(tmp_path):
    src = _clean_pdf(tmp_path)
    out = tmp_path / "sub" / "result.pdf"
    rep = tmp_path / "sub" / "my_report.csv"
    out.parent.mkdir()
    assert _run([str(src), "-o", str(out), "--report", str(rep)]) == 0
    assert out.is_file()
    assert rep.is_file()
    assert not (tmp_path / "plans_linked.pdf").exists()


def test_input_file_is_never_modified(tmp_path):
    src = _clean_pdf(tmp_path)
    before = src.read_bytes()
    assert _run([str(src)]) == 0
    assert src.read_bytes() == before


def test_missing_file_exits_1_and_creates_nothing(tmp_path, capsys):
    assert _run([str(tmp_path / "nope.pdf")]) == 1
    assert not (tmp_path / "nope_linked.pdf").exists()
    assert capsys.readouterr().err.strip() != ""


def test_non_pdf_file_exits_1(tmp_path):
    bad = tmp_path / "x.pdf"
    bad.write_text("not a pdf")
    assert _run([str(bad)]) == 1
    assert not (tmp_path / "x_linked.pdf").exists()


def test_encrypted_pdf_exits_1(tmp_path):
    src = _clean_pdf(tmp_path)
    enc = tmp_path / "enc.pdf"
    with pikepdf.open(src) as pdf:
        pdf.save(enc, encryption=pikepdf.Encryption(owner="o", user="u"))
    assert _run([str(enc)]) == 1


def test_zero_page_pdf_exits_1(tmp_path):
    empty = tmp_path / "empty.pdf"
    pikepdf.Pdf.new().save(empty)
    assert _run([str(empty)]) == 1


def test_output_equal_to_input_exits_1_and_keeps_input(tmp_path):
    src = _clean_pdf(tmp_path)
    before = src.read_bytes()
    assert _run([str(src), "-o", str(src)]) == 1
    assert src.read_bytes() == before


def test_no_arguments_exits_2():
    assert _run([]) == 2


def test_unknown_option_exits_2(tmp_path):
    src = _clean_pdf(tmp_path)
    assert _run([str(src), "--bogus"]) == 2


def test_installed_console_script_runs(tmp_path):
    script = Path(sys.executable).parent / "pdf-autolink"
    assert script.exists(), "script 'pdf-autolink' chưa được cài (pyproject [project.scripts])"
    src = _clean_pdf(tmp_path)
    proc = subprocess.run(
        [str(script), str(src)], capture_output=True, text=True, timeout=120, check=False
    )
    assert proc.returncode == 0
    assert proc.stdout.strip().splitlines()[-1].startswith("pdf-autolink: 2 pages, 2 links added")
    assert (tmp_path / "plans_linked.pdf").is_file()


@pytest.mark.parametrize("flag", ["--help"])
def test_help_exits_0(flag, capsys):
    assert _run([flag]) == 0
    assert "pdf-autolink" in capsys.readouterr().out
