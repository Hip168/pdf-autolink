"""[1-2] resolve: 4 trạng thái linked / self / ambiguous / unmatched."""

from __future__ import annotations

from pdf_autolink.models import Reference, RefKind, SheetIndex, Status
from pdf_autolink.resolver import resolve


def _ref(code: str, page: int, kind: RefKind = RefKind.SHEET) -> Reference:
    return Reference(page, code, kind, code, (0.0, 0.0, 10.0, 10.0))


def _index() -> SheetIndex:
    return SheetIndex(
        by_code={"A101": [0], "A102": [1], "A103": [2, 3]},
        unrecognized=[4],
        page_codes={0: "A101", 1: "A102", 2: "A103", 3: "A103", 4: None},
    )


def test_code_on_exactly_one_other_page_is_linked():
    (r,) = resolve([_ref("A102", 0)], _index())
    assert r.status is Status.LINKED
    assert r.target_page == 1


def test_code_on_same_page_is_self():
    (r,) = resolve([_ref("A101", 0)], _index())
    assert r.status is Status.SELF


def test_code_on_two_pages_is_ambiguous_without_target():
    (r,) = resolve([_ref("A103", 0)], _index())
    assert r.status is Status.AMBIGUOUS
    assert r.target_page is None


def test_ambiguous_even_when_source_page_is_one_of_the_candidates():
    (r,) = resolve([_ref("A103", 2)], _index())
    assert r.status is Status.AMBIGUOUS
    assert r.target_page is None


def test_unknown_code_is_unmatched_without_target():
    (r,) = resolve([_ref("Z999", 0)], _index())
    assert r.status is Status.UNMATCHED
    assert r.target_page is None


def test_detail_reference_resolves_by_its_code():
    ref = Reference(0, "3/A102", RefKind.DETAIL, "A102", (0.0, 0.0, 10.0, 10.0))
    (r,) = resolve([ref], _index())
    assert r.ref is ref
    assert r.status is Status.LINKED
    assert r.target_page == 1


def test_order_and_length_are_preserved():
    refs = [_ref("Z999", 0), _ref("A102", 0), _ref("A103", 1), _ref("A101", 0)]
    out = resolve(refs, _index())
    assert [x.ref for x in out] == refs
    assert [x.status for x in out] == [
        Status.UNMATCHED,
        Status.LINKED,
        Status.AMBIGUOUS,
        Status.SELF,
    ]


def test_empty_input_gives_empty_output():
    assert resolve([], _index()) == []
