# Quyết định

## Luật riêng dự án (người dùng chốt khi init, 2026-11-21)

1. **Không hỏi người dùng**: đội tự quyết, ghi lý do vào file này.
2. **Công cụ test do đội tự chốt** (gợi ý: pytest + PDF mẫu tự sinh bằng reportlab hoặc tương tự, giấy phép thoáng).
3. **Công cụ test / khung test đã khoá** chỉ được sửa khi đã chạy quá 10 lần mà **TẤT CẢ** TESTER, TEST-LEAD và DEV đều kết luận lỗi do công cụ test; ghi biên bản vào `.team/conflicts/`.
4. **Hạn mức**: ngày 2026-11-21 không để hạn mức tuần của Claude vượt 60%.

Còn lại theo `~/.claude/team/CONVENTIONS.md`.

## Quyết định kiến trúc

(BA sẽ điền)

- **D1 (2026-11-21) BA tự duyệt bản nháp issue** theo Luật riêng (1) — người dùng giao toàn quyền, không hỏi.
- **D2 Chia 2 đề mục độc lập:** 1 lõi CLI; 2 app kéo-thả. Hợp đồng chung duy nhất = giao diện CLI trong `features/1-loi-gan-link-giao-dien.md`; đề mục 2 test bằng CLI giả → chạy song song, merge thứ tự nào cũng được.
- **D3 Đề mục 1 chọn kiến trúc "sạch"** (logic thuần tách I/O, `TextSource` Protocol) thay vì "tối thiểu": lý do — OCR là mở rộng đã biết trước (brief), logic thuần test được không cần PDF; chi phí thêm ~4 file nhỏ. Lấy từ bản tối thiểu: mã thoát rõ ràng, cảnh báo toạ độ xoay/CropBox là rủi ro số 1.
- **D4 Đề mục 2 chọn AppleScript droplet** (nguồn text, `osacompile` dựng lại được, test được trên CI macOS) thay vì Automator (bundle khó diff) / Shortcuts (không kéo-thả vào biểu tượng, không dựng từ nguồn).
- **D5 Idempotent bằng so trùng Rect (IoU ≥ 0.9) + cùng trang đích**, không dùng dấu /NM: coi cả link có sẵn của file gốc là "đã có" (chấp nhận).
- **D6 `A-501` ≠ `A501`**, không gộp biến thể mã (để sau nếu cần).
- **D7 CI** ma trận ubuntu + macos, Python 3.11/3.12 (repo public → phút miễn phí); job macOS cần cho đề mục 2.
- **D8** Thứ tự merge 1 → 2: nhánh 2 không có pyproject nên CI chỉ chạy test macOS sau khi cập nhật theo main có đề mục 1. Hợp đồng headless của app: `features/2-app-keo-tha.md` mục "Chốt thêm".
