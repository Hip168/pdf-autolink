"""CSV report of resolved references."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from .models import RefKind, Resolved, SheetIndex, Status

CSV_COLUMNS = ["source_page", "text", "kind", "target_page", "status", "note"]


def write_report(resolved: Sequence[Resolved], index: SheetIndex, path: str | Path) -> None:
    """Write one row per reference plus one row per page whose sheet id was not found.

    Page numbers are 1-based; target_page is empty when there is no target.
    """
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for res in resolved:
            target = "" if res.target_page is None else res.target_page + 1
            writer.writerow(
                [res.ref.page + 1, res.ref.text, res.ref.kind, target, res.status, ""]
            )
        for page in index.unrecognized:
            writer.writerow(
                [page + 1, "", RefKind.SHEET, "", Status.UNMATCHED, "sheet id not recognized"]
            )
