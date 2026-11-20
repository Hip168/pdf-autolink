# Hợp đồng giao diện — đề mục 1 (DEV ↔ TESTER)

Tên module, chữ ký, giá trị mặc định dưới đây là hợp đồng. Đổi → `CẦN BA`.

```python
# pdf_autolink/models.py
@dataclass(frozen=True)
class WordBox:
    text: str
    x0: float; y0: float; x1: float; y1: float   # toạ độ HIỂN THỊ: pt, gốc trên-trái, sau xoay, tương đối mép CropBox
    size: float

@dataclass(frozen=True)
class PageText:
    index: int            # 0-based
    width: float          # kích thước hiển thị (đã xoay)
    height: float
    words: list[WordBox]

class RefKind(StrEnum):  SHEET = "sheet";  DETAIL = "detail"
class Status(StrEnum):   LINKED = "linked"; UNMATCHED = "unmatched"; SELF = "self"; AMBIGUOUS = "ambiguous"

@dataclass(frozen=True)
class Reference:
    page: int             # 0-based trang nguồn
    text: str             # nguyên văn: "A101" hoặc "3/A501"
    kind: RefKind
    code: str             # mã đích đã chuẩn hoá
    rect: tuple[float, float, float, float]   # hiển thị, trên-trái (x0, y0, x1, y1)

@dataclass(frozen=True)
class Resolved:
    ref: Reference
    status: Status
    target_page: int | None   # 0-based

@dataclass
class SheetIndex:
    by_code: dict[str, list[int]]   # mã → các trang 0-based
    unrecognized: list[int]
    page_codes: dict[int, str | None]

@dataclass
class Result:
    sheets: SheetIndex
    resolved: list[Resolved]
    links_added: int
    links_skipped_existing: int

class PdfAutolinkError(Exception): ...   # file lỗi / mã hoá / 0 trang / output == input

# pdf_autolink/config.py
@dataclass(frozen=True)
class Config:
    title_block_region: tuple[float, float, float, float] = (0.55, 0.70, 1.0, 1.0)  # tỉ lệ trang, gốc trên-trái
    sheet_regex: str = r"[A-Z]{1,2}[-.]?\d{1,4}(?:[.\-]\d{1,3})?"
    detail_regex: str = r"(\d{1,3})\s*/\s*({sheet})"   # {sheet} thay bằng sheet_regex
    stack_max_gap_factor: float = 1.5
    iou_duplicate: float = 0.9

def normalize_code(text: str) -> str          # upper + bỏ khoảng trắng; giữ . và -

# pdf_autolink/geometry.py
def display_to_pdf_rect(rect: tuple[float, float, float, float], *,
                        cropbox: tuple[float, float, float, float], rotate: int
                        ) -> tuple[float, float, float, float]   # user space PDF, x0<x1, y0<y1

# pdf_autolink/textsource.py
class TextSource(Protocol):
    def pages(self) -> Iterator[PageText]: ...
class PdfplumberSource:
    def __init__(self, path: str | Path) -> None: ...
    def pages(self) -> Iterator[PageText]: ...

# pdf_autolink/sheetid.py
def identify_sheet(page: PageText, cfg: Config) -> str | None
def identify_all(pages: Sequence[PageText], cfg: Config) -> SheetIndex

# pdf_autolink/refs.py
def find_references(page: PageText, own_code: str | None, cfg: Config) -> list[Reference]

# pdf_autolink/resolver.py
def resolve(refs: Sequence[Reference], index: SheetIndex) -> list[Resolved]

# pdf_autolink/annotate.py
def add_links(pdf: pikepdf.Pdf, resolved: Sequence[Resolved], pages: Sequence[PageText],
              cfg: Config) -> tuple[int, int]      # (added, skipped_existing)

# pdf_autolink/report.py
CSV_COLUMNS = ["source_page", "text", "kind", "target_page", "status", "note"]
def write_report(resolved: Sequence[Resolved], index: SheetIndex, path: str | Path) -> None

# pdf_autolink/pipeline.py
def autolink(input: str | Path, output: str | Path, report: str | Path | None = None,
             cfg: Config = Config(), source: TextSource | None = None) -> Result

# pdf_autolink/cli.py
def main(argv: Sequence[str] | None = None) -> int
#   pdf-autolink INPUT [-o OUTPUT] [--report REPORT.csv]
#   mặc định OUTPUT = <stem>_linked.pdf, REPORT = <stem>_linked.csv (cạnh OUTPUT)
#   0 = xong; 1 = PdfAutolinkError / file không tồn tại; 2 = sai tham số (argparse)
#   Dòng cuối stdout: "pdf-autolink: <n_pages> pages, <links_added> links added, <skipped> existing, <unmatched> unmatched, <ambiguous> ambiguous"
```

Helper test (TESTER sở hữu): `tests/helpers/make_pdf.py` — `PageSpec(code, texts=[(x, y, size, str)], rotate=0, cropbox=None, size=(w, h))`, `build(pages, path)`; mã trang vẽ ở góc dưới phải cỡ 24, chữ khác cỡ 8–10; `/Rotate`, `/CropBox` đặt bằng pikepdf sau khi sinh. Vị trí kỳ vọng trong test tính bằng hằng số, **không** gọi `geometry`.

## Chốt thêm (BA, 2026-11-21 — trả lời giả định của TESTER-1)
1. **`self`:** không tạo link; `Resolved.target_page` = trang của mã đó (chính trang nguồn).
2. **Dòng tóm tắt CLI:** `<unmatched>` = số Resolved có `status == unmatched` (KHÔNG tính trang không nhận mã); `<ambiguous>` tương tự.
3. **`--report` mặc định:** `OUTPUT` đổi đuôi `.csv`, cùng thư mục với OUTPUT (vd `-o /x/out.pdf` → `/x/out.csv`; không có `-o` → `<stem>_linked.csv` cạnh input).
4. **CSV:** dòng "trang không nhận mã" có `text=""`, `kind="sheet"`, `target_page=""`, `status="unmatched"`, `note="sheet id not recognized"`; các dòng còn lại `note=""`.
5. **`autolink(report=None)`:** không ghi CSV (CLI luôn truyền đường dẫn).
6. **Phân biệt hoa thường:** mã chỉ khớp chữ HOA (`sheet_regex` như hợp đồng, không cờ IGNORECASE) — `a101` không phải mã.
7. **`PageSpec.texts`:** `(x, y, size, text)` theo toạ độ hiển thị, `y` = đường cơ sở tính từ mép trên, chữ nằm ngang (theo docstring của TESTER-1).

## Chốt thêm 2 (BA, 2026-11-21 — ghi lại tham số DEV-1 đã chọn, TEST-LEAD đề nghị)
- **Khoảng cách dọc của bong bóng 2 dòng** = khe hở giữa hai hộp chữ: `y0(từ dưới) − y1(từ trên)` ≤ `stack_max_gap_factor × size`, với `size = max(cỡ hai từ)`.
- **Lệch ngang 2 dòng:** chồng ngang, hoặc |tâm x lệch| ≤ 2 × size. Nhiều ứng viên → mã gần nhất phía dưới.
- **Bong bóng 1 dòng ghép nhiều từ:** tối đa 3 từ liền kề; liền kề = cùng dòng (tâm dọc lệch ≤ nửa chiều cao) và khe ngang ≤ cỡ chữ của từ trước.
- **Thứ tự kết quả `find_references`:** sắp theo `(y0, x0)`.
