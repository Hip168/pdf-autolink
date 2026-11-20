# pdf-autolink

Auto-hyperlink multi-page construction/engineering drawing PDF sets on macOS — in one run.

**Status:** early development.

## Goal

Given a drawing set (one multi-page PDF), produce a copy where:

- **Sheet numbers** (e.g. `A101`, `M201`) appearing anywhere link to the page whose title block carries that number.
- **Detail callouts / section bubbles** such as `3/A501` (text may be split across two lines) link to sheet `A501`.
- **Sheet index / table of contents** entries link to each sheet.

Links are standard PDF Link annotations (`/GoTo` actions), so they work in Adobe Acrobat, Bluebeam Revu (Windows), macOS Preview and other viewers. No dependency on Bluebeam.

A CSV report lists every link created and every reference that could not be matched.

## Planned interface

- Command-line tool (`pdf-autolink input.pdf -o output.pdf`)
- macOS drag-and-drop app (wrapper around the CLI)
- Optional OCR for scanned sets (via `ocrmypdf`) — later

## Tech

Python, [pikepdf](https://github.com/pikepdf/pikepdf) and [pdfplumber](https://github.com/jsvine/pdfplumber). PyMuPDF is intentionally avoided (AGPL) to keep the project MIT-licensed.

## License

MIT — see [LICENSE](LICENSE).
