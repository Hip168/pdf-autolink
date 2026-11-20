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
- macOS drag-and-drop app (wrapper around the CLI) — see [docs/app-macos.md](docs/app-macos.md)
- Optional OCR for scanned sets (via `ocrmypdf`) — later

## Install

Requires Python 3.11+. From a clone of this repository:

```bash
uv tool install .      # or: pipx install .
```

## Usage

```bash
pdf-autolink plans.pdf                      # -> plans_linked.pdf + plans_linked.csv
pdf-autolink plans.pdf -o out/linked.pdf    # -> out/linked.pdf + out/linked.csv
pdf-autolink plans.pdf --report refs.csv
```

The input file is never modified. The last line printed is a summary, e.g.
`pdf-autolink: 5 pages, 6 links added, 0 existing, 1 unmatched, 0 ambiguous`.

Exit codes: `0` done (even with unmatched references), `1` input missing / not a PDF /
encrypted / no pages / output path equals input, `2` invalid arguments.

What gets linked:

- A page's **sheet number** is the largest word matching the sheet pattern
  (e.g. `A101`, `M201`, `S-101`, `E0.01`) inside the title-block area (bottom-right of the page).
- Every other occurrence of a sheet number on any page (including a sheet index) links to that page.
- Detail callouts `3/A501`, on one line or stacked (`3` above `A501`), become one link to `A501`.
- Running the tool again on its own output adds no duplicate links; existing annotations are kept.

CSV report columns: `source_page,text,kind,target_page,status,note` (1-based pages).
`status` is `linked`, `self` (reference to its own page, not linked), `ambiguous`
(sheet number found on several pages, not linked) or `unmatched`. Pages whose sheet number
could not be found get a row with `note = sheet id not recognized`.

## Limitations

- Needs a text layer: scanned sets must be OCR'd first (built-in OCR is planned).
- Vertical text inside a page is not read; whole-page `/Rotate` is supported.
- Sheet numbers are matched upper-case only; `A-501` and `A501` are different sheets.
- The title-block area (bottom-right) is fixed; there is no CLI option to change it.

## Tech

Python, [pikepdf](https://github.com/pikepdf/pikepdf) and [pdfplumber](https://github.com/jsvine/pdfplumber). PyMuPDF is intentionally avoided (AGPL) to keep the project MIT-licensed.

## License

MIT — see [LICENSE](LICENSE).
