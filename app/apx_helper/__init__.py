"""Backend para rellenar las plantillas APX Global Sheet a partir de contratos JSON."""

from .generator import Issue, RenderResult, render
from .contracts import ContractError, LIBRARY, TRANSACTION, detect_kind

__all__ = [
    "ContractError",
    "Issue",
    "LIBRARY",
    "TRANSACTION",
    "RenderResult",
    "detect_kind",
    "render",
]

__version__ = "1.0.0"
