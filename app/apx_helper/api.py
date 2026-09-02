"""API REST y UI para generar las hojas APX a partir de contratos JSON."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .contracts import LIBRARY, TRANSACTION, ContractError, detect_kind, validate
from .generator import render

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STATIC_DIR = Path(__file__).parent / "static"

KIND_LABELS = {TRANSACTION: "transacción", LIBRARY: "librería"}

ContractPayload = dict[str, Any] | list[dict[str, Any]]

app = FastAPI(
    title="APX Helper",
    version=__version__,
    description=(
        "Rellena las plantillas APX Global Sheet (transacción y librería) desde un contrato JSON. "
        "Acepta una lista de contratos de transacción para generar un libro con una hoja por transacción."
    ),
)


def _first(payload: ContractPayload) -> dict[str, Any]:
    return payload[0] if isinstance(payload, list) else payload


def _check_expected_kind(payload: ContractPayload, expected_kind: str | None) -> str:
    try:
        kind = detect_kind(_first(payload))
    except (ContractError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc) or "El archivo no contiene contratos.") from exc
    if expected_kind and expected_kind != kind:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Elegiste cargar una {KIND_LABELS[expected_kind]}, pero el archivo contiene "
                f"un contrato de {KIND_LABELS[kind]}."
            ),
        )
    return kind


def _render_or_error(data: ContractPayload, library_id: str | None, name: str | None):
    try:
        return render(data, library_id=library_id, name=name)
    except ContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _parse_json(payload: bytes) -> ContractPayload:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El contrato supera el tamaño máximo permitido.")
    try:
        contract = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"El archivo no es un JSON válido: {exc}") from exc
    if not isinstance(contract, (dict, list)):
        raise HTTPException(status_code=422, detail="El contrato debe ser un objeto o una lista JSON.")
    return contract


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/api/contracts/validate")
def validate_contract(contract: ContractPayload = Body(...)) -> dict[str, Any]:
    items = contract if isinstance(contract, list) else [contract]
    try:
        kinds = [validate(item) for item in items]
    except ContractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"valid": True, "kinds": kinds}


@app.post("/api/contracts/process")
async def process(
    file: UploadFile = File(..., description="Contrato JSON generado por el agente."),
    expected_kind: str | None = Form(default=None, description="'transaction' o 'library'."),
    library_id: str | None = Form(default=None),
) -> dict[str, Any]:
    """Procesa el contrato importado y devuelve la hoja APX junto al reporte de pendientes."""
    if expected_kind and expected_kind not in KIND_LABELS:
        raise HTTPException(status_code=400, detail="expected_kind debe ser 'transaction' o 'library'.")

    contract = _parse_json(await file.read(MAX_UPLOAD_BYTES + 1))
    kind = _check_expected_kind(contract, expected_kind)
    result = _render_or_error(contract, library_id, None)

    return {
        "kind": kind,
        "kindLabel": KIND_LABELS[kind],
        "filename": result.filename,
        "sheets": result.workbook.sheetnames,
        "summary": result.summary,
        "issues": [issue.as_dict() for issue in result.issues],
        "fileBase64": base64.b64encode(result.to_bytes()).decode("ascii"),
    }


@app.post("/api/contracts/xlsx")
def generate(
    contract: ContractPayload = Body(...),
    library_id: str | None = Query(default=None, description="Identificador de librería, p. ej. ADVSR500."),
    name: str | None = Query(default=None, description="Nombre base alternativo para el archivo."),
) -> Response:
    result = _render_or_error(contract, library_id, name)
    return Response(
        content=result.to_bytes(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-APX-Issues": str(len(result.issues)),
        },
    )


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
