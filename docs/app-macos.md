# macOS drag-and-drop app

`PDF AutoLink.app` is a small AppleScript droplet: drop one or more PDF files onto its icon and
each one is run through the `pdf-autolink` command-line tool. It is a thin wrapper — all the
linking work is done by the CLI.

## 1. Install the CLI

The app needs `pdf-autolink` to be installed first:

```bash
uv tool install git+https://github.com/Hip168/pdf-autolink
```

This puts the command in `~/.local/bin/pdf-autolink`. The app looks for the CLI in this order:

1. the `PDF_AUTOLINK_CLI` environment variable (full path to the executable);
2. `~/.local/bin/pdf-autolink`, `/opt/homebrew/bin/pdf-autolink`, `/usr/local/bin/pdf-autolink`;
3. `command -v pdf-autolink` in a login `zsh` shell.

If none is found the app shows "chưa cài pdf-autolink" (not installed) together with the install
command above.

## 2. Build the app

On a Mac, from the repository root:

```bash
scripts/build-app.sh            # -> dist/PDF AutoLink.app
scripts/build-app.sh ~/Desktop  # or any other output folder
```

The script compiles `app/PDFAutoLink.applescript` with `osacompile`, replaces any previous build,
sets the bundle id `io.github.pdf-autolink.app`, signs it ad hoc (`codesign --sign -`) and prints
the path of the app. Move the app wherever you like (e.g. `/Applications` or the Dock).

## 3. Drag and drop

- Drop one or more files onto the app icon. Only files ending in `.pdf` (any case) are processed;
  other files are counted as skipped.
- For each PDF the CLI writes `<name>_linked.pdf` and `<name>_linked.csv` next to the original.
- When all files are done a notification shows `<ok> file xong, <errors> lỗi, <skipped> bỏ qua`
  (done / errors / skipped). If any file failed, a dialog lists each failed file with the last
  line of the CLI's error output.
- Double-clicking the app (instead of dropping files) only shows a short how-to dialog.

**Existing output is overwritten:** running the app again on the same PDF replaces the previous
`<name>_linked.pdf` and `<name>_linked.csv` without asking.

## 4. Gatekeeper and notification permission

- The app is signed ad hoc, not notarized. If you built it yourself on the same Mac it opens
  normally. If you copied it from another Mac and macOS blocks it, right-click the app → **Open**
  → **Open**, or allow it in **System Settings → Privacy & Security**.
- Notifications are shown by macOS on behalf of the app (they may appear as coming from "Script
  Editor"). If you see no notification, enable it in **System Settings → Notifications**. Errors
  are always shown in a dialog as well, so nothing is lost if notifications are off.

## For testing / automation

Setting `PDF_AUTOLINK_HEADLESS=1` disables all dialogs and notifications: the `open` handler returns
the result text (printed by `osascript`) and raises an error with the same text when any file
failed. The first line is the summary, then one line per processed file:
`<file name>: <last line of CLI output>`. Example:

```bash
PDF_AUTOLINK_HEADLESS=1 osascript \
  -e 'set s to load script POSIX file "/path/to/PDF AutoLink.app/Contents/Resources/Scripts/main.scpt"' \
  -e 'tell s to open {POSIX file "/path/to/set.pdf"}'
```
