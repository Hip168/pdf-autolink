"""pdf-autolink: add GoTo links to drawing-set PDFs."""

from .config import Config
from .models import PdfAutolinkError

__version__ = "0.1.0"

__all__ = ["Config", "PdfAutolinkError", "__version__"]
