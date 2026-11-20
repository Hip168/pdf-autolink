"""Test app kéo-thả macOS (đề mục 2) bằng CLI giả; chỉ chạy trên macOS."""

from __future__ import annotations

import os
import plistlib
import pwd
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="chỉ macOS")

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "scripts" / "build-app.sh"
SUMMARY = "pdf-autolink: 3 pages, 5 links added, 0 existing, 1 unmatched, 0 ambiguous"
TIMEOUT = 120

# Nguồn: .team/features/2-app-keo-tha.md, mục "Chốt thêm" (BA, 2026-11-21).
# Gọi headless: nạp main.scpt bằng `load script`, rồi `tell s to open {POSIX file ...}`.
# `open` trả chuỗi (osascript in ra stdout): dòng 1 = "<ok> file xong, <lỗi> lỗi,
# <bỏ qua> bỏ qua", các dòng sau = "<tên file>: <dòng cuối output CLI>". Có lỗi =>
# `error` với chuỗi đó (osascript thoát != 0, stderr bắt đầu "execution error: ").
DRIVER = [
    "-e",
    "on run argv",
    "-e",
    "set s to load script POSIX file (item 1 of argv)",
    "-e",
    "set fl to {}",
    "-e",
    "repeat with i from 2 to count of argv",
    "-e",
    "set end of fl to POSIX file (item i of argv)",
    "-e",
    "end repeat",
    "-e",
    "tell s to open fl",
    "-e",
    "end run",
]


@pytest.fixture(scope="module")
def app(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    r = subprocess.run(
        ["bash", str(BUILD), str(out)],
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        cwd=ROOT,
    )
    assert r.returncode == 0, r.stderr
    return out / "PDF AutoLink.app"


def make_cli(tmp: Path, body: str) -> tuple[Path, Path]:
    log = tmp / "cli-args.log"
    cli = tmp / "fake-cli.sh"
    cli.write_text('#!/bin/bash\nprintf "%s\\n" "$1" >> ' + f"'{log}'\n" + body + "\n")
    cli.chmod(0o755)
    return cli, log


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def run_app(app: Path, files: list[Path], env_extra: dict[str, str]):
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(app.parent),
        "PDF_AUTOLINK_HEADLESS": "1",
        **env_extra,
    }
    script = app / "Contents" / "Resources" / "Scripts" / "main.scpt"
    return subprocess.run(
        ["/usr/bin/osascript", *DRIVER, str(script), *map(str, files)],
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        env=env,
    )


def test_build_tao_app_dung_cau_truc(app: Path) -> None:
    plist = app / "Contents" / "Info.plist"
    assert plist.is_file()
    assert (app / "Contents/Resources/Scripts/main.scpt").is_file()
    lint = subprocess.run(
        ["plutil", "-lint", str(plist)],
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr
    info = plistlib.loads(plist.read_bytes())
    assert info["CFBundleIdentifier"] == "io.github.pdf-autolink.app"
    assert info["CFBundleName"] == "PDF AutoLink"


def test_build_chay_lai_xoa_ban_cu(tmp_path: Path) -> None:
    def build() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(BUILD), str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=ROOT,
        )

    first = build()
    assert first.returncode == 0, first.stderr
    marker = tmp_path / "PDF AutoLink.app" / "Contents" / "ban-cu.txt"
    marker.write_text("cu")
    second = build()
    assert second.returncode == 0, second.stderr
    assert not marker.exists()
    assert (tmp_path / "PDF AutoLink.app/Contents/Info.plist").is_file()
    assert str(tmp_path / "PDF AutoLink.app") in second.stdout


def test_pdf_ten_dac_biet_den_cli_dung_duong_dan(app: Path, tmp_path: Path) -> None:
    d = tmp_path / "Tài liệu d'Artagnan  & co"
    d.mkdir()
    pdf = d / "Bản vẽ tầng 1's.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    cli, log = make_cli(tmp_path, f'echo "{SUMMARY}"')
    r = run_app(app, [pdf], {"PDF_AUTOLINK_CLI": str(cli)})
    assert r.returncode == 0, r.stderr
    got = log.read_text(encoding="utf-8").splitlines()
    assert [nfc(x) for x in got] == [nfc(str(pdf))]
    lines = nfc(r.stdout).splitlines()
    assert lines[0] == "1 file xong, 0 lỗi, 0 bỏ qua"
    assert lines[1:] == [nfc(f"{pdf.name}: {SUMMARY}")]


def test_nhieu_file_va_duoi_pdf_hoa_thuong(app: Path, tmp_path: Path) -> None:
    a, b = tmp_path / "a.PDF", tmp_path / "b.Pdf"
    for p in (a, b):
        p.write_bytes(b"%PDF-1.4\n")
    cli, log = make_cli(tmp_path, f'echo "{SUMMARY}"')
    r = run_app(app, [a, b], {"PDF_AUTOLINK_CLI": str(cli)})
    assert r.returncode == 0, r.stderr
    assert sorted(log.read_text().splitlines()) == sorted([str(a), str(b)])
    lines = r.stdout.splitlines()
    assert lines[0] == "2 file xong, 0 lỗi, 0 bỏ qua"
    assert sorted(lines[1:]) == [f"a.PDF: {SUMMARY}", f"b.Pdf: {SUMMARY}"]


def test_file_txt_bi_bo_qua_cli_khong_duoc_goi(app: Path, tmp_path: Path) -> None:
    txt = tmp_path / "ghi chu.txt"
    txt.write_text("x")
    cli, log = make_cli(tmp_path, f'echo "{SUMMARY}"')
    r = run_app(app, [txt], {"PDF_AUTOLINK_CLI": str(cli)})
    assert r.returncode == 0, r.stderr
    assert not log.exists()
    assert r.stdout.splitlines()[0] == "0 file xong, 0 lỗi, 1 bỏ qua"
    assert "ghi chu.txt" not in r.stdout


def test_hon_hop_pdf_va_txt_dem_dung(app: Path, tmp_path: Path) -> None:
    pdf, txt = tmp_path / "ok.pdf", tmp_path / "x.docx"
    pdf.write_bytes(b"%PDF-1.4\n")
    txt.write_text("x")
    cli, log = make_cli(tmp_path, f'echo "{SUMMARY}"')
    r = run_app(app, [pdf, txt], {"PDF_AUTOLINK_CLI": str(cli)})
    assert r.returncode == 0, r.stderr
    assert log.read_text().splitlines() == [str(pdf)]
    lines = r.stdout.splitlines()
    assert lines[0] == "1 file xong, 0 lỗi, 1 bỏ qua"
    assert lines[1:] == [f"ok.pdf: {SUMMARY}"]
    assert "x.docx" not in r.stdout


def test_cli_thoat_khac_0_bao_loi_kem_ten_file(app: Path, tmp_path: Path) -> None:
    pdf = tmp_path / "hong nang.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    cli, log = make_cli(tmp_path, 'echo "loi: khong doc duoc"; exit 1')
    r = run_app(app, [pdf], {"PDF_AUTOLINK_CLI": str(cli)})
    assert r.returncode != 0
    assert "execution error: 0 file xong, 1 lỗi, 0 bỏ qua\n" in r.stderr
    assert "hong nang.pdf: loi: khong doc duoc" in r.stderr
    assert log.read_text().splitlines() == [str(pdf)]


def test_mot_file_loi_mot_file_ok_van_xu_ly_ca_hai(app: Path, tmp_path: Path) -> None:
    good, bad = tmp_path / "good.pdf", tmp_path / "bad.pdf"
    for p in (good, bad):
        p.write_bytes(b"%PDF-1.4\n")
    cli, log = make_cli(
        tmp_path, f'case "$1" in *bad.pdf) echo oops; exit 1;; esac; echo "{SUMMARY}"'
    )
    r = run_app(app, [bad, good], {"PDF_AUTOLINK_CLI": str(cli)})
    assert r.returncode != 0
    assert sorted(log.read_text().splitlines()) == sorted([str(good), str(bad)])
    assert "execution error: 1 file xong, 1 lỗi, 0 bỏ qua\n" in r.stderr
    assert "bad.pdf: oops" in r.stderr
    assert f"good.pdf: {SUMMARY}" in r.stderr


def _cli_that_tren_may(home: Path) -> str | None:
    """Trả về đường dẫn pdf-autolink thật nếu app có thể dò ra (khi đó test bị skip)."""
    real_home = pwd.getpwuid(os.getuid()).pw_dir
    for c in (
        Path(real_home) / ".local/bin/pdf-autolink",
        Path("/opt/homebrew/bin/pdf-autolink"),
        Path("/usr/local/bin/pdf-autolink"),
    ):
        if c.exists():
            return str(c)
    r = subprocess.run(
        ["/bin/zsh", "-lc", "command -v pdf-autolink"],
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        env={"PATH": "", "HOME": str(home)},
    )
    return r.stdout.strip() or None


def test_cli_khong_ton_tai_bao_chua_cai(app: Path, tmp_path: Path) -> None:
    # Dò đúng như app thấy: zsh -lc chạy với PATH rỗng + HOME giả (không dính PATH của
    # pytest/.venv). Ba nơi file cố định thì kiểm ở máy thật; có thì skip.
    home = tmp_path / "home-trong"
    home.mkdir()
    found = _cli_that_tren_may(home)
    if found:
        pytest.skip(f"máy đã có pdf-autolink ({found}); không dựng được ca 'chưa cài'")
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    r = run_app(
        app,
        [pdf],
        {"PDF_AUTOLINK_CLI": str(tmp_path / "khong-co"), "PATH": "", "HOME": str(home)},
    )
    assert r.returncode != 0
    assert "chưa cài pdf-autolink" in r.stderr


def test_tai_lieu_app_macos_ton_tai_va_readme_tro_toi() -> None:
    doc = ROOT / "docs" / "app-macos.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8").lower()
    for muc in ("install", "build", "drag", "gatekeeper", "overwrit"):
        assert muc in text, muc
    assert "docs/app-macos.md" in (ROOT / "README.md").read_text(encoding="utf-8")
