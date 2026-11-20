#!/bin/bash
# Build "PDF AutoLink.app" (AppleScript droplet) from app/PDFAutoLink.applescript.
# Usage: scripts/build-app.sh [output-dir]   (default: dist/)
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ] || ! command -v osacompile >/dev/null 2>&1; then
  echo "build-app.sh: requires macOS with osacompile" >&2
  exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
out="${1:-$root/dist}"
app="$out/PDF AutoLink.app"
plist="$app/Contents/Info.plist"

mkdir -p "$out"
rm -rf "$app"
osacompile -o "$app" "$root/app/PDFAutoLink.applescript"
/usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string io.github.pdf-autolink.app" "$plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier io.github.pdf-autolink.app" "$plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleName PDF AutoLink" "$plist" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleName string PDF AutoLink" "$plist"
if command -v codesign >/dev/null 2>&1; then
  codesign --force --sign - "$app"
fi
echo "$app"
