"""[1-3] write_report: cột, đánh số trang 1-based, dòng trang không nhận mã."""

from __future__ import annotations

import csv

from pdf_autolink.report import CSV_COLUMNS, write_report

from pdf_autolink.models import Reference, RefKind, Resolved, SheetIndex, Status

BOX = (0.0, 0.0, 10.0, 10.0)


def _res(text, source, kind, code, status, target):
    return Resolved(Reference(source, text, kind, code, BOX), status, target)


def _index(unrecognized=()):
    return SheetIndex(by_code={}, unrecognized=list(unrecognized), page_codes={})


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_columns_constant_matches_contract():
    assert CSV_COLUMNS == ["source_page", "text", "kind", "target_page", "status", "note"]


def test_header_row_is_exactly_the_contract_columns(tmp_path):
    out = tmp_path / "r.csv"
    write_report([], _index(), out)
    with open(out, newline="", encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == CSV_COLUMNS


def test_rows_use_one_based_pages_and_status_strings(tmp_path):
    out = tmp_path / "r.csv"
    resolved = [
        _res("A102", 0, RefKind.SHEET, "A102", Status.LINKED, 1),
        _res("3/A103", 1, RefKind.DETAIL, "A103", Status.LINKED, 2),
    ]
    write_report(resolved, _index(), out)
    rows = _read(out)
    assert len(rows) == 2
    assert rows[0]["source_page"] == "1"
    assert rows[0]["text"] == "A102"
    assert rows[0]["kind"] == "sheet"
    assert rows[0]["target_page"] == "2"
    assert rows[0]["status"] == "linked"
    assert rows[1]["source_page"] == "2"
    assert rows[1]["text"] == "3/A103"
    assert rows[1]["kind"] == "detail"
    assert rows[1]["target_page"] == "3"


def test_target_is_empty_when_no_target(tmp_path):
    out = tmp_path / "r.csv"
    resolved = [
        _res("Z999", 0, RefKind.SHEET, "Z999", Status.UNMATCHED, None),
        _res("A103", 0, RefKind.SHEET, "A103", Status.AMBIGUOUS, None),
    ]
    write_report(resolved, _index(), out)
    rows = _read(out)
    assert [r["target_page"] for r in rows] == ["", ""]
    assert [r["status"] for r in rows] == ["unmatched", "ambiguous"]


def test_self_status_is_written(tmp_path):
    out = tmp_path / "r.csv"
    write_report([_res("A101", 0, RefKind.SHEET, "A101", Status.SELF, 0)], _index(), out)
    (row,) = _read(out)
    assert row["status"] == "self"
    assert row["source_page"] == "1"


def test_each_unrecognized_page_gets_one_unmatched_row_with_note(tmp_path):
    out = tmp_path / "r.csv"
    resolved = [_res("A102", 0, RefKind.SHEET, "A102", Status.LINKED, 1)]
    write_report(resolved, _index(unrecognized=[2, 4]), out)
    rows = _read(out)
    flagged = [r for r in rows if r["note"] == "sheet id not recognized"]
    assert [r["source_page"] for r in flagged] == ["3", "5"]
    assert all(r["status"] == "unmatched" for r in flagged)
    assert all(r["text"] == "" and r["kind"] == "sheet" for r in flagged)
    assert all(r["note"] == "" for r in rows if r not in flagged)
    assert all(r["target_page"] == "" for r in flagged)
    assert len(rows) == 3


def test_self_row_has_target_page_of_itself(tmp_path):
    out = tmp_path / "r.csv"
    write_report([_res("A101", 0, RefKind.SHEET, "A101", Status.SELF, 0)], _index(), out)
    (row,) = _read(out)
    assert row["target_page"] == "1"


def test_no_unrecognized_pages_means_no_note_rows(tmp_path):
    out = tmp_path / "r.csv"
    write_report([_res("A102", 0, RefKind.SHEET, "A102", Status.LINKED, 1)], _index(), out)
    assert all(r["note"] != "sheet id not recognized" for r in _read(out))


def test_accepts_str_path(tmp_path):
    out = tmp_path / "r.csv"
    write_report([], _index(unrecognized=[0]), str(out))
    assert len(_read(out)) == 1
