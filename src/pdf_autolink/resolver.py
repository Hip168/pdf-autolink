"""Match references to target pages (pure logic)."""

from __future__ import annotations

from collections.abc import Sequence

from .models import Reference, Resolved, SheetIndex, Status


def resolve(refs: Sequence[Reference], index: SheetIndex) -> list[Resolved]:
    out: list[Resolved] = []
    for ref in refs:
        pages = index.by_code.get(ref.code, [])
        if not pages:
            out.append(Resolved(ref, Status.UNMATCHED, None))
        elif len(pages) > 1:
            out.append(Resolved(ref, Status.AMBIGUOUS, None))
        elif pages[0] == ref.page:
            out.append(Resolved(ref, Status.SELF, pages[0]))
        else:
            out.append(Resolved(ref, Status.LINKED, pages[0]))
    return out
