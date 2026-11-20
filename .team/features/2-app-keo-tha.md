# Đề mục 2 — App kéo-thả macOS · nhánh `2-app-keo-tha` · Cỡ: nhỏ

## Mục tiêu
Người không rành dòng lệnh kéo một hoặc nhiều PDF thả vào biểu tượng "PDF AutoLink.app" → mỗi file chạy CLI `pdf-autolink` → thông báo macOS kết quả.

## Phạm vi / Ngoài phạm vi
- Trong: AppleScript droplet + script dựng app + test macOS + tài liệu.
- Ngoài: ký/notarize, giao diện cấu hình, tiến trình (progress bar), sửa CLI.

## Kiến trúc đã chọn — AppleScript droplet (xem `decisions.md` D4)
- `app/PDFAutoLink.applescript`
  - `on open droppedItems` → `processFiles(droppedItems)`; `on run` → hộp thoại hướng dẫn kéo thả.
  - `findCli()`: ưu tiên biến môi trường `PDF_AUTOLINK_CLI`; rồi `~/.local/bin/pdf-autolink`, `/opt/homebrew/bin`, `/usr/local/bin`; cuối cùng `/bin/zsh -lc 'command -v pdf-autolink'`. Không thấy → báo "chưa cài pdf-autolink" kèm lệnh cài.
  - Mỗi file: chỉ nhận đuôi `.pdf` (không phân biệt hoa thường), còn lại đếm "bỏ qua"; chạy `do shell script "export LANG=en_US.UTF-8; " & quoted form of cli & " " & quoted form of p & " 2>&1"` bọc `with timeout of 3600 seconds`; lỗi → ghi tên file + dòng cuối thông báo; thành công → giữ dòng cuối stdout (tóm tắt) nguyên văn.
  - Tổng kết: `display notification "<ok> file xong, <lỗi> lỗi, <bỏ qua> bỏ qua" with title "PDF AutoLink"`; có lỗi → thêm hộp thoại chi tiết.
  - `PDF_AUTOLINK_HEADLESS=1` → không hộp thoại/thông báo; in kết quả ra stdout và `error` khi có lỗi (để test/CI không treo).
- `scripts/build-app.sh [thư-mục-ra]` (mặc định `dist/`): kiểm Darwin + `osacompile`; xoá bản cũ; `osacompile -o "<ra>/PDF AutoLink.app"`; PlistBuddy đặt `CFBundleIdentifier=io.github.pdf-autolink.app`, `CFBundleName=PDF AutoLink`; `codesign --force --sign -` nếu có; in đường dẫn app.
- `docs/app-macos.md`: cài CLI, dựng app, kéo thả, Gatekeeper/quyền thông báo, file ra bị ghi đè.

## Phụ thuộc
Chỉ dựa vào hợp đồng CLI ở `1-loi-gan-link-giao-dien.md` (`pdf-autolink INPUT`, thoát 0 = xong, dòng cuối stdout = tóm tắt). Test dùng **CLI giả** (script shell nhỏ) qua `PDF_AUTOLINK_CLI` → làm song song với đề mục 1.

## Task
### [2-1] Droplet + script dựng app + test
- [ ] `scripts/build-app.sh <tmp>` thoát 0, tạo app có `Contents/Info.plist` (`plutil -lint` OK, bundle id đúng), `Contents/Resources/Scripts/main.scpt`.
- [ ] Gọi handler ở chế độ headless với CLI giả cho PDF nằm trong thư mục có dấu cách, dấu nháy đơn và tên tiếng Việt → CLI giả nhận đúng đường dẫn (so sánh sau chuẩn hoá Unicode NFC) và kết quả báo 1 file xong.
- [ ] File `.txt` → bỏ qua, CLI không được gọi; CLI giả thoát ≠ 0 → kết quả báo 1 lỗi kèm tên file; `PDF_AUTOLINK_CLI` trỏ file không tồn tại + PATH rỗng → lỗi "chưa cài".
- [ ] Test chỉ chạy trên macOS (`skipif sys.platform != "darwin"`), mỗi subprocess có timeout.
### [2-2] Tài liệu
- [ ] `docs/app-macos.md` đủ các mục trên; README thêm một dòng trỏ tới.

## Chốt thêm (BA, 2026-11-21 — trả lời CẦN BA của TESTER-2)
- **Cách gọi headless (hợp đồng test):** `PDF_AUTOLINK_HEADLESS=1 osascript -e 'set s to load script POSIX file "<app>/Contents/Resources/Scripts/main.scpt"' -e 'tell s to open {POSIX file "<pdf1>", POSIX file "<pdf2>"}'` — tức gọi handler `on open` của script đã biên dịch.
- **Kết quả headless:** handler `open` **trả về** chuỗi (osascript in ra stdout): dòng 1 = `"<ok> file xong, <lỗi> lỗi, <bỏ qua> bỏ qua"`; mỗi dòng sau = `"<tên file>: <dòng cuối output của CLI>"` cho từng file đã chạy (thành công hay lỗi).
- **Có ≥ 1 lỗi ở headless:** `error` với đúng chuỗi trên (osascript thoát ≠ 0, chuỗi ở stderr).
- **Không tìm thấy CLI:** thông báo chứa nguyên văn `chưa cài pdf-autolink` (headless → `error` thông báo đó).
- **pyproject:** đề mục 2 không tạo pyproject; test chỉ dùng thư viện chuẩn + pytest. Thứ tự merge: **1 trước, 2 sau** (2 cập nhật theo main rồi CI mới chạy test macOS) — `decisions.md` D8.
