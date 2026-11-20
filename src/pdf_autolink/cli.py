"""Command-line entry point: pdf-autolink INPUT [-o OUTPUT] [--report REPORT.csv]."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .models import PdfAutolinkError, Status
from .pipeline import autolink


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdf-autolink",
        description="Add GoTo links for sheet numbers, detail callouts and sheet indexes.",
    )
    parser.add_argument("input", help="drawing-set PDF")
    parser.add_argument("-o", "--output", help="output PDF (default: <stem>_linked.pdf)")
    parser.add_argument("--report", help="CSV report (default: OUTPUT with .csv suffix)")
    args = parser.parse_args(argv)

    src = Path(args.input)
    out = Path(args.output) if args.output else src.with_name(f"{src.stem}_linked.pdf")
    report = Path(args.report) if args.report else out.with_suffix(".csv")
    try:
        result = autolink(src, out, report)
    except PdfAutolinkError as exc:
        print(f"pdf-autolink: error: {exc}", file=sys.stderr)
        return 1

    unmatched = sum(r.status is Status.UNMATCHED for r in result.resolved)
    ambiguous = sum(r.status is Status.AMBIGUOUS for r in result.resolved)
    print(
        f"pdf-autolink: {len(result.sheets.page_codes)} pages, {result.links_added} links added, "
        f"{result.links_skipped_existing} existing, {unmatched} unmatched, {ambiguous} ambiguous"
    )
    return 0
