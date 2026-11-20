"""End-to-end: read text, find references, add links, save, report."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pikepdf
from pdfminer.psexceptions import PSException

from .annotate import add_links
from .config import Config
from .models import PdfAutolinkError, Result
from .refs import find_references
from .report import write_report
from .resolver import resolve
from .sheetid import identify_all
from .textsource import PdfplumberSource, TextSource

_DEFAULT_CONFIG = Config()


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


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
    if report is not None and Path(report).resolve() in (src.resolve(), out.resolve()):
        raise PdfAutolinkError("report must be different from input and output")
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

        try:
            pages = list((source or PdfplumberSource(src)).pages())
        except PSException as exc:
            raise PdfAutolinkError(f"cannot read text from PDF: {src} ({exc})") from exc
        index = identify_all(pages, cfg)
        refs = [r for p in pages for r in find_references(p, index.page_codes.get(p.index), cfg)]
        resolved = resolve(refs, index)
        added, skipped = add_links(pdf, resolved, pages, cfg)

        # Write to a temp file next to the output, then rename.
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(suffix=".pdf", dir=out.parent)
            os.close(fd)
            try:
                pdf.save(tmp)
                os.chmod(tmp, 0o666 & ~_umask())  # mkstemp creates 0600
                os.replace(tmp, out)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise PdfAutolinkError(f"cannot write output: {out} ({exc})") from exc

    if report is not None:
        try:
            Path(report).parent.mkdir(parents=True, exist_ok=True)
            write_report(resolved, index, report)
        except OSError as exc:
            raise PdfAutolinkError(f"cannot write report: {report} ({exc})") from exc
    return Result(index, resolved, added, skipped)
