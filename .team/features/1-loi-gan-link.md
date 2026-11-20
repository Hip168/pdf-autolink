# Đề mục 1 — Lõi gắn link · nhánh `1-loi-gan-link` · Cỡ: thường

## Mục tiêu
CLI Python: đọc bộ PDF bản vẽ nhiều trang (có lớp chữ), tự gắn PDF Link annotation chuẩn: mã bản vẽ / bong bóng chi tiết / mục lục → trang đích; xuất báo cáo CSV.

## Phạm vi
- Nhận mã trang (khung tên), tham chiếu mã trang ở mọi nơi (kể cả mục lục), bong bóng chi tiết 1 dòng `3/A501` và 2 dòng (`3` trên, `A501` dưới).
- Link GoTo `/Fit`, viền 0, toạ độ đúng với `/Rotate` 0/90/180/270 và CropBox lệch gốc.
- Giữ annotation có sẵn; chạy lại không nhân đôi link.
- CSV + CLI + đóng gói `pdf-autolink`.

## Ngoài phạm vi
OCR bản scan; chữ xoay dọc; cờ CLI chỉnh vùng khung tên; app kéo-thả (đề mục 2); gộp `A-501` với `A501`.

## Kiến trúc đã chọn — hướng "sạch" (xem `decisions.md` D3)
Tầng logic thuần (không I/O PDF) tách khỏi I/O; OCR sau này chỉ thêm một `TextSource`.
```
src/pdf_autolink/
  __init__.py   __version__, re-export autolink, Config, PdfAutolinkError
  models.py     dataclass frozen + StrEnum, không import thư viện PDF
  config.py     Config
  geometry.py   display_to_pdf_rect (thuần)
  textsource.py TextSource (Protocol) + PdfplumberSource
  sheetid.py    identify_sheet / identify_all (thuần)
  refs.py       find_references (thuần)
  resolver.py   resolve (thuần)
  annotate.py   add_links (pikepdf, idempotent)
  report.py     write_report (CSV)
  pipeline.py   autolink()
  cli.py        main()
tests/helpers/make_pdf.py  dựng PDF mẫu bằng reportlab (+ pikepdf đặt /Rotate, /CropBox)
```
Luồng: PDF → PdfplumberSource → [PageText] → identify_all → SheetIndex → find_references từng trang → resolve → add_links (geometry) → lưu (ghi tạm rồi đổi tên) → write_report → tóm tắt CLI.

Hợp đồng chữ ký: **`1-loi-gan-link-giao-dien.md`**.

## Thuật toán chốt
- **Mã trang:** từ nằm trong `title_block_region` (tâm từ, toạ độ hiển thị), fullmatch `sheet_regex`, chọn cỡ chữ lớn nhất; hoà → thấp nhất rồi phải nhất. Không có → `None`, trang vào `unrecognized`.
- **Chuẩn hoá mã:** `upper()` + bỏ khoảng trắng; giữ `.` và `-` (`A-501` ≠ `A501`).
- **Thứ tự tìm tham chiếu:** (1) detail 1 dòng (một từ, hoặc nhiều từ liền kề cùng dòng ghép lại khớp `detail_regex`); (2) detail 2 dòng: từ chỉ 1–3 chữ số, ngay dưới (khoảng cách dọc ≤ `stack_max_gap_factor` × cỡ chữ, chồng ngang hoặc lệch tâm ≤ 2 × cỡ chữ) là từ khớp mã → rect = hợp 2 hộp; (3) mã đơn lẻ còn lại; từ đã dùng ở (1)(2) không dùng lại. Từ trong khung tên có mã == mã trang → bỏ (không phát ra); mã == mã trang ở chỗ khác → phát ra, resolver gán `self`.
- **Trạng thái:** mã có đúng 1 trang: trùng trang nguồn → `self`, khác → `linked`; ≥ 2 trang → `ambiguous` (không link); không có → `unmatched`.
- **Annotation:** `/Type /Annot /Subtype /Link /Rect [..] /Border [0 0 0] /A << /S /GoTo /D [trang_đích /Fit] >>`; thêm vào `/Annots` (tạo nếu thiếu, xử lý `/Annots` gián tiếp), không xoá cái cũ, không đụng `/Contents`. **Idempotent:** bỏ qua nếu trang nguồn đã có `/Link` GoTo cùng trang đích và Rect IoU ≥ 0.9.
- **Toạ độ:** pdfplumber trả toạ độ hiển thị (đã xoay, gốc trên-trái, tương đối CropBox) → `display_to_pdf_rect` gỡ xoay rồi lật y theo CropBox. Đúng/sai do test quyết, không giả định.

## Task
### [1-1] Khung gói + mô hình + toạ độ + đọc chữ
- [ ] `pyproject.toml` (hatchling, Python ≥ 3.11, deps pikepdf + pdfplumber, nhóm dev pytest + reportlab + ruff, script `pdf-autolink`), `uv.lock`; `uv sync --group dev` chạy được.
- [ ] `models.py`, `config.py` đúng hợp đồng.
- [ ] `display_to_pdf_rect` cho Rotate 0/90/180/270 × CropBox lệch gốc: hộp chữ vẽ ở vị trí biết trước → Rect khớp ±2pt.
- [ ] `PdfplumberSource.pages()` trả `PageText` toạ độ hiển thị, có `size`, kích thước hiển thị đúng với trang xoay.
### [1-2] Nhận mã trang + tham chiếu + phân giải
- [ ] `identify_sheet`/`identify_all`: nhận A101, M201, S-101, E0.01; trang không có mã → `unrecognized`; chữ lớn ngoài vùng khung tên không bị chọn; nhiều ứng viên → cỡ lớn nhất.
- [ ] `find_references`: mục lục liệt kê mã → mỗi mã một Reference SHEET; detail 1 dòng và 2 dòng → một Reference DETAIL (không thêm SHEET trùng); 2 dòng cách xa hơn ngưỡng → chỉ SHEET; mã của chính trang trong khung tên → không phát ra.
- [ ] `resolve`: đủ 4 trạng thái theo luật trên.
### [1-3] Ghi link + CSV + pipeline + CLI
- [ ] `add_links`: cấu trúc annotation đúng như trên, `/D[0]` là đúng đối tượng trang đích; giữ annotation có sẵn (link URI + Text); chạy 2 lần → số `/Link` không đổi, lần 2 `added == 0`; `pikepdf` mở lại file không lỗi.
- [ ] `write_report`: cột `source_page,text,kind,target_page,status,note` (trang 1-based, đích rỗng nếu không có); mỗi trang không nhận mã có một dòng `status=unmatched`, `note="sheet id not recognized"`.
- [ ] `autolink()` e2e: bộ 5 trang có mục lục + bong bóng + một trang xoay → link đúng.
- [ ] CLI: mặc định `<stem>_linked.pdf` + `<stem>_linked.csv` cạnh input; thoát 0 khi xong (kể cả có unmatched); 1 khi file không tồn tại / không phải PDF / mã hoá / 0 trang / `-o` trùng input; 2 khi sai tham số; dòng cuối stdout là tóm tắt có số link mới.
- [ ] README tiếng Anh: cài (`uv tool install .` / `pipx install .`), dùng, giới hạn.
