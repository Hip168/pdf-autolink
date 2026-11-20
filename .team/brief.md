# Brief — pdf-autolink

## Yêu cầu gốc

Công cụ chạy trên macOS: một lần chạy là bộ PDF bản vẽ nhiều trang tự có hyperlink.

- **Mã bản vẽ** (A101, M201, …) xuất hiện ở bất kỳ đâu → link tới trang có mã đó trong khung tên.
- **Bong bóng chi tiết** kiểu `3/A501` (chữ có thể tách 2 dòng) → link tới trang A501.
- **Mục lục / sheet index** → link tới từng trang.
- Link là **PDF Link annotation chuẩn (GoTo)** để mở được trên Windows / Bluebeam Revu / Acrobat / Preview.
- **Không phụ thuộc Bluebeam** (Revu for Mac đã EOL).
- **Python**, `pikepdf` + `pdfplumber` (tránh PyMuPDF vì AGPL).
- **Báo cáo CSV**: các link đã gắn / các tham chiếu không khớp.
- **CLI + app kéo-thả macOS** (Automator/Shortcuts hoặc tương tự).
- Tuỳ chọn **OCR cho bản scan** (`ocrmypdf`) — phần mở rộng sau.

## Lựa chọn đã chốt

- Repo GitHub **public**, giấy phép **MIT**. Không đưa thông tin cá nhân vào repo.
- Người dùng giao **full quyền** cho đội tự làm A→Z.
- Đội tự chốt công cụ test.

## Luật riêng dự án

1. **Không hỏi người dùng**: tự quyết và ghi lý do vào `.team/decisions.md`.
2. **Công cụ test do đội tự chốt** (gợi ý: pytest + PDF mẫu tự sinh bằng reportlab hoặc tương tự, giấy phép thoáng).
3. **Công cụ test / khung test đã khoá** chỉ được sửa khi đã chạy quá 10 lần mà **TẤT CẢ** TESTER, TEST-LEAD và DEV đều kết luận lỗi do công cụ test; ghi biên bản vào `.team/conflicts/`.
4. **Hạn mức**: ngày 2026-11-21 không để hạn mức tuần của Claude vượt 60%.

Còn lại theo `~/.claude/team/CONVENTIONS.md` như cũ.
