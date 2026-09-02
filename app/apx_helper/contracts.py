"""Carga y validación de los contratos JSON contra su formato de referencia."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .settings import contracts_dir

TRANSACTION = "transaction"
LIBRARY = "library"

TRANSACTION_ROOT_KEY = "TRANSACTION - FUNCTIONAL DESCRIPTION"
LIBRARY_ROOT_KEY = "LIBRARY - FUNCTIONAL GROUPING DESCRIPTION"

_SCHEMA_FILES = {
    TRANSACTION: "contrato-transaccion.json",
    LIBRARY: "contrato-libreria.json",
}
_OPTION_FILES = {
    TRANSACTION: "opciones-transaccion.json",
    LIBRARY: "opciones-libreria.json",
}

SCALAR_TYPES = (str, int, float, bool)


class ContractError(ValueError):
    """El JSON recibido no respeta el contrato de referencia."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"No se encontró el archivo de referencia {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"{path.name} no es un JSON válido: {exc}") from exc


@lru_cache(maxsize=None)
def _load_reference(filename: str) -> Any:
    return _read_json(contracts_dir() / filename)


def load_schema(kind: str) -> dict:
    return _load_reference(_SCHEMA_FILES[kind])


def load_options(kind: str) -> dict[str, list[str]]:
    return _load_reference(_OPTION_FILES[kind])


def detect_kind(data: Any) -> str:
    if not isinstance(data, dict):
        raise ContractError("El contrato debe ser un objeto JSON.")
    if TRANSACTION_ROOT_KEY in data:
        return TRANSACTION
    if LIBRARY_ROOT_KEY in data:
        return LIBRARY
    raise ContractError(
        "No se reconoce el tipo de contrato: falta "
        f"'{TRANSACTION_ROOT_KEY}' o '{LIBRARY_ROOT_KEY}' en la raíz."
    )


def _validate(node: Any, schema: Any, path: str, errors: list[str]) -> None:
    if isinstance(schema, dict):
        if not isinstance(node, dict):
            errors.append(f"{path or 'raíz'}: se esperaba un objeto y llegó {type(node).__name__}.")
            return
        for key, sub_schema in schema.items():
            sub_path = f"{path}.{key}" if path else key
            if key not in node:
                errors.append(f"{sub_path}: clave obligatoria ausente.")
                continue
            _validate(node[key], sub_schema, sub_path, errors)
        for key in node:
            if key not in schema:
                sub_path = f"{path}.{key}" if path else key
                errors.append(f"{sub_path}: clave no definida en el contrato.")
    elif isinstance(schema, list):
        if not isinstance(node, list):
            errors.append(f"{path}: se esperaba un array y llegó {type(node).__name__}.")
            return
        item_schema = schema[0] if schema else {}
        for index, item in enumerate(node):
            _validate(item, item_schema, f"{path}[{index}]", errors)
    else:
        if node is not None and not isinstance(node, SCALAR_TYPES):
            errors.append(f"{path}: se esperaba un valor simple y llegó {type(node).__name__}.")


def validate(data: Any, kind: str | None = None) -> str:
    """Valida la estructura del contrato y devuelve su tipo."""
    kind = kind or detect_kind(data)
    errors: list[str] = []
    _validate(data, load_schema(kind), "", errors)
    if errors:
        raise ContractError(
            "El contrato no respeta el formato de referencia:\n  - " + "\n  - ".join(errors)
        )
    return kind


def load_contracts(path: str | Path) -> list[tuple[dict, str]]:
    """Lee un JSON con un contrato o con una lista de contratos y valida cada uno."""
    data = _read_json(Path(path))
    items = data if isinstance(data, list) else [data]
    if not items:
        raise ContractError(f"{path}: el archivo no contiene ningún contrato.")
    return [(item, validate(item)) for item in items]
