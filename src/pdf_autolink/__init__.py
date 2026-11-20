"""pdf-autolink: add GoTo links to drawing-set PDFs."""

from .config import Config
from .models import PdfAutolinkError
from .pipeline import autolink

__version__ = "0.1.0"

__all__ = ["Config", "PdfAutolinkError", "__version__", "autolink"]
