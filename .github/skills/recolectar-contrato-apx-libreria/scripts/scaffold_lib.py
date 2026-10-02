"""Genera el esqueleto determinista del contrato de una librería APX Tipo B.

Uso: python scaffold_lib.py <raiz_proyecto> <salida.json> [--force]

La raíz es el proyecto cuyo `apx.json` declara `resource_type: "lib"`. Rellena desde el POM, la
interfaz pública y el análisis léxico del código: identificador, visibilidad, tipo de librería,
inventario de métodos `execute*` con su firma, librerías invocadas por método y parámetros de
entrada/salida expandidos desde la firma Java (y un nivel de campos si el DTO tiene fuente en el
proyecto). Todo lo que requiere interpretación queda como "__TODO__:<pista>" único y editable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_common import (  # noqa: E402
    MARKER,
    TODO,
    access_type_candidates,
    dto_fields,
    find_library,
    format_type,
    generic_arg,
    is_tautological,
    javadoc_summary,
    library_calls_in_text,
    library_type_from_pom,
    list_interface_methods,
    method_spans,
    normalize,
    pom_description,
    read_text,
)
from callgraph_lib import build_graph_for_method  # noqa: E402


def param_rows(root: Path, name: str, java_type: str, label: str) -> list[dict]:
    fmt = format_type(java_type)
    rows = [{
        "Name of APX field": name,
        "Mandatory?": f"{TODO}:Mandatory:{label}:{name}",
        "Format Type": fmt if fmt else MARKER,
        "Description": f"{TODO}:Description:{label}:{name}",
    }]
    simple = java_type.rsplit(".", 1)[-1].rstrip("[]")
    if fmt == "bean":
        fields = dto_fields(root, simple)
        if not fields:
            rows[0]["Description"] = f"{TODO}:Description:{label}:{name} (fuente del DTO '{simple}' no disponible en el repositorio)"
        for field_name, field_type, _ in fields:
            rows.extend(param_rows(root, f"{name}.{field_name}", field_type, label))
    elif fmt in {"list", "set", "array", "queue"}:
        inner = generic_arg(java_type)
        if inner and format_type(inner) == "bean":
            for field_name, field_type, _ in dto_fields(root, inner):
                rows.extend(param_rows(root, f"{name}.{field_name}", field_type, label))
    return rows


def other_access_rows(accesses: list[tuple[str, str, str]]) -> list[dict]:
    return [
        {
            "Access Type": access_type,
            "Country": f"{TODO}:Country:{bean or access_type}",
            "Identifier": f"{TODO}:Identifier:{bean or access_type} ({evidence})",
            "Access": f"{TODO}:Access:{bean or access_type}",
            "Description": f"{TODO}:Description:{bean or access_type}",
        }
        for access_type, bean, evidence in accesses
    ]


def build_method(root: Path, impl_java: Path, method, accesses: list[tuple[str, str, str]]) -> dict:
    graph = build_graph_for_method(root, impl_java, method.name)
    source = read_text(impl_java)
    spans = [(s, e) for n, s, e in method_spans(source) if n == method.name]
    body = source[spans[0][0]:spans[0][1]] if spans else ""
    libs = library_calls_in_text(body)
    for path, _, s, e in graph.methods:
        if path != impl_java:
            libs = sorted(set(libs) | set(library_calls_in_text(read_text(path)[s:e])))

    input_rows: list[dict] = []
    for java_type, param_name in method.params:
        input_rows.extend(param_rows(root, param_name, java_type, "IN"))

    output_rows: list[dict] = []
    if method.return_type and method.return_type not in {"void", "Void"}:
        output_rows.extend(param_rows(root, "returnValue", method.return_type, "OUT"))

    brief = javadoc_summary(method.javadoc)
    return {
        "Method name": method.name,
        "Brief description": brief if brief and not is_tautological(brief, method.name) else f"{TODO}:Brief:{method.name}",
        "DESCRIPTION OF THE FUNCTIONALITY": f"{TODO}:Functionality:{method.name}",
        "Accessed libraries": [
            {
                "Library Identifier": lib,
                "Country": f"{TODO}:Country:{lib}.{call}",
                "Method": call,
                "Description": f"{TODO}:Library:{lib}.{call}",
            }
            for lib, call in libs
        ],
        "Other accesses": other_access_rows(accesses),
        "Error Management": [
            {"Error Code": code, "Description of the error situation": f"{TODO}:ErrorDescription:{method.name}:{code}"}
            for code in graph.first_emission_order()
        ],
        "Event that is generated": [],
        "PARAMETERS": {
            "Input Parameters": input_rows,
            "Output Parameters": output_rows,
        },
    }


def build(root: Path) -> dict:
    library = find_library(root)
    methods = list_interface_methods(library.interface_java)
    if not methods:
        raise SystemExit(f"{library.library_id}: no se encontró ningún método público en {library.interface_java}")

    accesses = sorted({c for arc in library.arc_xmls for c in access_type_candidates(arc)})
    method_blocks = [build_method(root, library.impl_java, method, accesses) for method in methods]

    description = pom_description(library.pom_interface) or pom_description(library.pom_parent) or MARKER

    return {
        "LIBRARY - FUNCTIONAL GROUPING DESCRIPTION": description,
        "TECHNICAL DATA": {
            "Library Identifier": library.library_id,
            "Visibility": "Public",
            "Library Type": library_type_from_pom(library),
            "For other, indicate": "",
        },
        "EXECUTE - METHODS SUMMARY": method_blocks,
    }


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 2:
        print(__doc__)
        return 2
    root, out = Path(args[0]).resolve(), Path(args[1])
    if out.exists() and "--force" not in sys.argv:
        print(f"{out} ya existe; usa --force para regenerarlo desde cero", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Esqueleto escrito en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
