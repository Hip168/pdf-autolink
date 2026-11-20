# INDEX — thư viện dự án
> Mọi agent đọc file này trước, rồi chỉ mở đúng file mình cần.
> Luật chung: ~/.claude/team/CONVENTIONS.md

| File | Nội dung | Ai đọc |
|---|---|---|
| .team/brief.md | Yêu cầu gốc + lựa chọn đã chốt + luật riêng dự án | BA, DEV, TESTER |
| .team/stack.md | Ngôn ngữ, framework, lệnh cài/chạy/test | DEV, TESTER |
| .team/decisions.md | Quyết định kiến trúc, quan hệ giữa các đề mục, luật riêng dự án | BA, DEV |
| .team/plan.md | Đề mục X → nhánh → issue [X-y] | Tất cả |
| .team/features/X-*.md | Chi tiết từng đề mục | DEV-X, TESTER-X |
| .team/tests/X.md | Sổ test của đề mục X | TESTER-X, TEST-LEAD-X, người dùng |
| .team/features/X-*-giao-dien.md | Chữ ký công khai (tên class/hàm/Key/ARB/đường dẫn file) — hợp đồng giữa DEV và TESTER | DEV-X, TESTER-X, TEST-LEAD-X |
| .team/conflicts/X.md | Chỗ DEV làm khác nhau | Người dùng, BA |
| .team/autonomy.md | Chế độ tự động + luật riêng dự án | Điều phối |
| .team/features/1-loi-gan-link.md | Đề mục 1: kiến trúc, thuật toán, task + tiêu chí | DEV-1, TESTER-1, TEST-LEAD |
| .team/features/1-loi-gan-link-giao-dien.md | Hợp đồng chữ ký module + CLI | DEV-1, TESTER-1, DEV-2, TESTER-2, TEST-LEAD |
| .team/features/2-app-keo-tha.md | Đề mục 2: droplet AppleScript, task + tiêu chí | DEV-2, TESTER-2, TEST-LEAD |
