"""End-to-end: read text, find references, add links, save, report."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pikepdf

from .annotate import add_links
from .config import Config
from .models import PdfAutolinkError, Result
from .refs import find_references
from .report import write_report
from .resolver import resolve
from .sheetid import identify_all
from .textsource import PdfplumberSource, TextSource

_DEFAULT_CONFIG = Config()


def autolink(
    input: str | Path,
    output: str | Path,
    report: str | Path | None = None,
    cfg: Config = _DEFAULT_CONFIG,
    source: TextSource | None = None,
) -> Result:
    src, out = Path(input), Path(output)
    if not src.is_file():
        raise PdfAutolinkError(f"input file not found: {src}")
    if out.resolve() == src.resolve():
        raise PdfAutolinkError("output must be different from input")
    try:
        pdf = pikepdf.open(src)
    except pikepdf.PasswordError as exc:
        raise PdfAutolinkError(f"encrypted PDF is not supported: {src}") from exc
    except pikepdf.PdfError as exc:
        raise PdfAutolinkError(f"not a readable PDF: {src} ({exc})") from exc
    with pdf:
        if pdf.is_encrypted:
            raise PdfAutolinkError(f"encrypted PDF is not supported: {src}")
        if len(pdf.pages) == 0:
            raise PdfAutolinkError(f"PDF has no pages: {src}")

        pages = list((source or PdfplumberSource(src)).pages())
        index = identify_all(pages, cfg)
        refs = [r for p in pages for r in find_references(p, index.page_codes.get(p.index), cfg)]
        resolved = resolve(refs, index)
        added, skipped = add_links(pdf, resolved, pages, cfg)

        # Write to a temp file next to the output, then rename.
        fd, tmp = tempfile.mkstemp(suffix=".pdf", dir=out.parent)
        os.close(fd)
        try:
            pdf.save(tmp)
            os.replace(tmp, out)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    if report is not None:
        write_report(resolved, index, report)
    return Result(index, resolved, added, skipped)
