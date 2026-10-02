"""Mapa de celdas de las plantillas APX Global Sheet v1.1.

Los números de fila/columna provienen de las plantillas de `hojas-apx/`.
Si BBVA publica una versión nueva, este es el único módulo que hay que revisar.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    """Campo escalar: una ruta del JSON escrita en una celda concreta."""

    path: tuple[str, ...]
    cell: str
    options: str | None = None
    optional: bool = False


@dataclass(frozen=True)
class Column:
    """Columna de una tabla. `literal` rellena un valor fijo (marcadores Input/Output)."""

    letter: str
    key: str | None = None
    options: str | None = None
    literal: str | None = None


@dataclass(frozen=True)
class Block:
    """Tabla de filas repetidas dentro de la plantilla."""

    path: tuple[str, ...]
    first_row: int
    last_row: int
    columns: tuple[Column, ...] = field(default_factory=tuple)
    # Si es obligatorio, quedar vacío se reporta como informacion faltante.
    required: bool = False

    @property
    def capacity(self) -> int:
        return self.last_row - self.first_row + 1


TECH = "TECHNICAL DATA"
PARAMS = "PARAMETERS"
INPUT = "Input Parameters"
OUTPUT = "Output Parameters"

# --------------------------------------------------------------------------------------
# Transacción — hoja "UUAATXXXYYZZ"
# --------------------------------------------------------------------------------------

TRANSACTION_FIELDS: tuple[Field, ...] = (
    Field(("TRANSACTION - FUNCTIONAL DESCRIPTION",), "B7"),
    Field(("EXECUTION FLOWS - DETAILED DESCRIPTION",), "B11"),
    Field((TECH, "Country"), "C17", options="Country"),
    Field((TECH, "Version"), "F17"),
    Field((TECH, "Migration - Origin from Host"), "C19"),
    Field((TECH, "Asynchronous?"), "C21", options="Asynchronous?"),
    Field((TECH, "Transactional?"), "F21", options="Transactional?"),
    # El encabezado "Transaction Identifier" está en C28; el valor va en la fila siguiente.
    Field((TECH, "Transaction Identifier"), "C29"),
)

TRANSACTION_BLOCKS: tuple[Block, ...] = (
    Block(
        (TECH, "Asynchronous Consumers"),
        25,
        27,
        (Column("C", "Service Identifier"),),
    ),
    Block(
        (TECH, "Accessed Libraries"),
        34,
        37,
        (
            Column("C", "Library Identifier"),
            Column("D", "Method"),
            Column("E", "Description"),
        ),
        required=True,
    ),
    Block(
        (TECH, "Error Management"),
        40,
        43,
        (
            Column("C", "Error Code"),
            Column("D", "Severity", options="Severity"),
            Column("E", "Description of the error situation"),
        ),
        required=True,
    ),
    Block(
        (TECH, "Events to which it is subscribed"),
        46,
        46,
        (Column("C", "Functional name"),),
    ),
    Block(
        (PARAMS, INPUT),
        52,
        56,
        (
            Column("B", literal="Input"),
            Column("C", "Name of APX field"),
            Column("D", "Mandatory?", options="Mandatory?"),
            Column("E", "APX data type", options="APX data type"),
            Column("F", "Description"),
        ),
        required=True,
    ),
    Block(
        (PARAMS, OUTPUT),
        60,
        64,
        (
            Column("B", literal="Output"),
            Column("C", "Name of APX field"),
            Column("D", "Mandatory?", options="Mandatory?"),
            Column("E", "APX data type", options="APX data type"),
            Column("F", "Description"),
        ),
        required=True,
    ),
)

# --------------------------------------------------------------------------------------
# Librería — hoja principal "UUAAR001"
# --------------------------------------------------------------------------------------

LIBRARY_FIELDS: tuple[Field, ...] = (
    Field(("LIBRARY - FUNCTIONAL GROUPING DESCRIPTION",), "B7"),
    Field((TECH, "Visibility"), "C15", options="Visibility"),
    Field((TECH, "Library Type"), "F15", options="Library Type"),
    Field((TECH, "For other, indicate"), "C16", optional=True),
)

# La plantilla no tiene celda para el identificador: da nombre a la hoja y al archivo.
LIBRARY_ID_PATH = (TECH, "Library Identifier")

LIBRARY_METHODS_BLOCK = Block(
    ("EXECUTE - METHODS SUMMARY",),
    23,
    32,
    (
        Column("B", "Method name"),
        Column("C", "Brief description"),
    ),
    required=True,
)

# --------------------------------------------------------------------------------------
# Librería — hoja por método "executeMethod"
# --------------------------------------------------------------------------------------

METHOD_TEMPLATE_SHEET = "executeMethod"

METHOD_FIELDS: tuple[Field, ...] = (
    Field(("Method name",), "B2"),
    Field(("DESCRIPTION OF THE FUNCTIONALITY",), "B5"),
)

METHOD_BLOCKS: tuple[Block, ...] = (
    Block(
        ("Accessed libraries",),
        12,
        13,
        (
            Column("C", "Library Identifier"),
            Column("D", "Country", options="Country"),
            Column("E", "Method"),
            Column("F", "Description"),
        ),
    ),
    Block(
        ("Other accesses",),
        16,
        17,
        (
            Column("C", "Access Type", options="Access Type"),
            Column("D", "Country", options="Country"),
            Column("E", "Identifier"),
            Column("F", "Access"),
            Column("G", "Description"),
        ),
    ),
    Block(
        ("Error Management",),
        20,
        21,
        (
            Column("C", "Error Code"),
            Column("D", "Description of the error situation"),
        ),
        required=True,
    ),
    Block(
        ("Event that is generated",),
        24,
        26,
        (
            Column("C", "Functional name"),
            Column("E", "Technical Identifier"),
        ),
    ),
    Block(
        (PARAMS, INPUT),
        31,
        35,
        (
            Column("B", literal="Input"),
            Column("C", "Name of APX field"),
            Column("D", "Mandatory?", options="Mandatory?"),
            Column("E", "Format Type", options="Format Type"),
            Column("F", "Description"),
        ),
        required=True,
    ),
    Block(
        (PARAMS, OUTPUT),
        39,
        43,
        (
            Column("B", literal="Output"),
            Column("C", "Name of APX field"),
            Column("D", "Mandatory?", options="Mandatory?"),
            Column("E", "Format Type", options="Format Type"),
            Column("F", "Description"),
        ),
    ),
)
