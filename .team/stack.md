# Stack

> BA chốt 2026-11-21 (người dùng giao toàn quyền, xem `decisions.md`).

- **Ngôn ngữ:** Python ≥ 3.11
- **Thư viện chạy:** `pikepdf` (ghi annotation, MPL-2.0), `pdfplumber` (đọc chữ + toạ độ, MIT). **Cấm PyMuPDF** (AGPL).
- **Quản lý môi trường:** `uv` (pyproject.toml, `uv.lock` commit vào repo)
- **Test:** `pytest`; PDF mẫu tự sinh trong test bằng `reportlab` (BSD) — không commit PDF nhị phân lớn
- **Lint:** `ruff check .` (cấu hình mặc định + `line-length = 100`)
- **App kéo-thả:** AppleScript droplet biên dịch bằng `osacompile` (chỉ macOS)
- **CI:** GitHub Actions, repo public → phút miễn phí; ma trận `ubuntu-latest` + `macos-latest`, Python 3.11 và 3.12

## Lệnh (chạy ở thư mục gốc repo / worktree)

```bash
uv sync --group dev            # cài phụ thuộc + công cụ dev
uv run ruff check .            # lint
uv run pytest -q               # test (test riêng macOS tự skip trên Linux)
uv run pdf-autolink in.pdf     # chạy CLI → in_linked.pdf + in_linked.csv
```

Không có giao diện web → **không bật soi trình duyệt** (§5c).
