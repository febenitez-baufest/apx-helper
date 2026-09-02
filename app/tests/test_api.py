import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apx_helper.api import app
from apx_helper.generator import INVALID, MISSING, REVIEW, render_transaction

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def transaction() -> dict:
    return json.loads((EXAMPLES / "ejemplo-transaccion.json").read_text(encoding="utf-8"))


@pytest.fixture
def library_bytes() -> bytes:
    return (EXAMPLES / "ejemplo-libreria.json").read_bytes()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _issues(result, severity):
    return [issue for issue in result.issues if issue.severity == severity]


def test_reporta_campo_vacio_y_sin_informacion(transaction):
    transaction["TECHNICAL DATA"]["Version"] = ""
    result = render_transaction(transaction)

    version = next(i for i in _issues(result, MISSING) if i.field.endswith("Version"))
    assert version.cell == "F17"
    origen = next(i for i in _issues(result, MISSING) if i.field.endswith("Migration - Origin from Host"))
    assert "no encontró información suficiente" in origen.message


def test_reporta_bloque_obligatorio_vacio(transaction):
    transaction["TECHNICAL DATA"]["Accessed Libraries"] = []
    result = render_transaction(transaction)

    issue = next(i for i in result.issues if i.field == "TECHNICAL DATA > Accessed Libraries")
    assert issue.severity == MISSING and issue.cell is None
    # Los arrays legítimamente vacíos no generan ruido.
    assert not [i for i in result.issues if "Events to which it is subscribed" in i.field]


def test_clasifica_revisar_e_invalido(transaction):
    transaction["TECHNICAL DATA"]["Country"] = "[REVISAR: BR]"
    transaction["PARAMETERS"]["Input Parameters"][0]["APX data type"] = "bean"
    result = render_transaction(transaction)

    assert any(i.severity == REVIEW and i.cell == "C17" for i in result.issues)
    assert any(i.severity == INVALID and i.cell == "E52" for i in result.issues)


def test_endpoint_process_devuelve_reporte_y_archivo(client, library_bytes):
    response = client.post(
        "/api/contracts/process",
        files={"file": ("ejemplo-libreria.json", library_bytes, "application/json")},
        data={"expected_kind": "library"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "ADVSR500 - APX Libraries Global Sheet V1.1.xlsx"
    assert payload["sheets"][0] == "ADVSR500"
    assert set(payload["summary"]) == {"missing", "review", "invalid"}
    assert payload["fileBase64"].startswith("UEsD")  # cabecera de un .xlsx


def test_endpoint_process_detecta_tipo_equivocado(client, library_bytes):
    response = client.post(
        "/api/contracts/process",
        files={"file": ("ejemplo-libreria.json", library_bytes, "application/json")},
        data={"expected_kind": "transaction"},
    )
    assert response.status_code == 409
    assert "librería" in response.json()["detail"]


def test_endpoint_process_rechaza_json_invalido(client):
    response = client.post(
        "/api/contracts/process",
        files={"file": ("roto.json", b"{ no es json", "application/json")},
        data={"expected_kind": "transaction"},
    )
    assert response.status_code == 400


def test_ui_se_sirve(client):
    assert client.get("/", follow_redirects=True).status_code == 200
