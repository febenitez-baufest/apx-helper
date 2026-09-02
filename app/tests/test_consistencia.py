"""Bloquea divergencias entre contratos, mapeo de la app y plantillas."""

import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from audit_contracts import (  # noqa: E402
    LIBRARY_COLUMNS,
    TRANSACTION_COLUMNS,
    mapped_paths,
    schema_paths,
    template_lists,
)

from apx_helper import layout  # noqa: E402
from apx_helper.contracts import LIBRARY, TRANSACTION, load_options, load_schema  # noqa: E402
from apx_helper.settings import (  # noqa: E402
    LIBRARY_TEMPLATE_GLOB,
    TRANSACTION_TEMPLATE_GLOB,
    find_template,
)


def _library_mapping():
    fields = layout.LIBRARY_FIELDS + tuple(
        layout.Field(("EXECUTE - METHODS SUMMARY", "[]") + f.path, f.cell, f.options)
        for f in layout.METHOD_FIELDS
    )
    blocks = (
        layout.Block(
            ("EXECUTE - METHODS SUMMARY",),
            layout.LIBRARY_METHODS_BLOCK.first_row,
            layout.LIBRARY_METHODS_BLOCK.last_row,
            layout.LIBRARY_METHODS_BLOCK.columns,
        ),
    ) + tuple(
        layout.Block(("EXECUTE - METHODS SUMMARY", "[]") + b.path, b.first_row, b.last_row, b.columns)
        for b in layout.METHOD_BLOCKS
    )
    return fields, blocks


def test_transaccion_cubre_todas_las_claves_del_contrato():
    mapped = mapped_paths(layout.TRANSACTION_FIELDS, layout.TRANSACTION_BLOCKS)
    assert schema_paths(load_schema(TRANSACTION)) == mapped


def test_libreria_cubre_todas_las_claves_del_contrato():
    fields, blocks = _library_mapping()
    # El identificador no tiene celda: nombra la hoja y el archivo.
    assert schema_paths(load_schema(LIBRARY)) - {layout.LIBRARY_ID_PATH} == mapped_paths(fields, blocks)


@pytest.mark.parametrize(
    "kind, pattern, columns",
    [
        (TRANSACTION, TRANSACTION_TEMPLATE_GLOB, TRANSACTION_COLUMNS),
        (LIBRARY, LIBRARY_TEMPLATE_GLOB, LIBRARY_COLUMNS),
    ],
)
def test_opciones_existen_en_los_desplegables_de_la_plantilla(kind, pattern, columns):
    lists = template_lists(find_template(pattern))
    for option_key, values in load_options(kind).items():
        allowed = lists[columns[option_key]]
        assert not set(values) - set(allowed), (
            f"'{option_key}': {sorted(set(values) - set(allowed))} no está en el desplegable "
            f"'{columns[option_key]}'. Ejecuta tools/sync_template_options.py."
        )
