"""[1-3] README tiếng Anh có đủ mục cài đặt, cách dùng, giới hạn."""

from __future__ import annotations

import re
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def _headings() -> list[str]:
    text = README.read_text(encoding="utf-8")
    return [m.group(1).strip().lower() for m in re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)]


def test_readme_has_install_usage_limitations_sections():
    heads = _headings()
    for name in ("install", "usage", "limitations"):
        assert any(name in h for h in heads), f"README thiếu mục {name}: {heads}"


def test_readme_mentions_install_commands_and_cli_name():
    text = README.read_text(encoding="utf-8")
    assert "uv tool install ." in text
    assert "pipx install ." in text
    assert "pdf-autolink" in text
