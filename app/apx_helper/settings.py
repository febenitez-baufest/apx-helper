"""Rutas de plantillas y contratos, configurables por variables de entorno."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TRANSACTION_TEMPLATE_GLOB = "*ransaction*.xlsx"
LIBRARY_TEMPLATE_GLOB = "*ibrar*.xlsx"


def _resolve(env_var: str, default: Path) -> Path:
    raw = os.environ.get(env_var)
    return Path(raw).expanduser().resolve() if raw else default


def templates_dir() -> Path:
    return _resolve("APX_TEMPLATES_DIR", REPO_ROOT / "hojas-apx")


def contracts_dir() -> Path:
    return _resolve("APX_CONTRACTS_DIR", REPO_ROOT / "contrato")


def find_template(pattern: str) -> Path:
    directory = templates_dir()
    matches = sorted(p for p in directory.glob(pattern) if not p.name.startswith("~$"))
    if not matches:
        raise FileNotFoundError(
            f"No se encontró ninguna plantilla que coincida con '{pattern}' en {directory}. "
            "Define APX_TEMPLATES_DIR si las hojas están en otra carpeta."
        )
    return matches[-1]
