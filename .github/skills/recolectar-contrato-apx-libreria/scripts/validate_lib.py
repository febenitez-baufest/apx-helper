"""Valida un contrato de librería APX Tipo B generado contra el esquema, el POM y el código.

Uso: python validate_lib.py <raiz_proyecto> <contrato_generado.json>

ERROR = incumplimiento bloqueante (corrige y vuelve a validar).
AVISO = revisar manualmente con evidencia; no bloquea.
Código de salida 0 solo si no hay ERRORES.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_common import (  # noqa: E402
    CODE,
    MARKER,
    TODO,
    TAUTOLOGY,
    find_library,
    format_type,
    library_calls_in_text,
    list_interface_methods,
    load_json_strict,
    method_spans,
    normalize,
    read_text,
)
from callgraph_lib import build_graph_for_method  # noqa: E402

REFERENCES = Path(__file__).resolve().parent.parent / "references"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_contract_template() -> dict:
    return json.loads((REFERENCES / "contrato-libreria.json").read_text(encoding="utf-8"))


def load_options() -> dict:
    return json.loads((REFERENCES / "opciones-libreria.json").read_text(encoding="utf-8"))


def check_shape(value, template, path: str, report: Report) -> None:
    if isinstance(template, dict):
        if not isinstance(value, dict):
            report.error(f"{path}: se esperaba objeto")
            return
        if list(value.keys()) != list(template.keys()):
            report.error(f"{path}: claves u orden distintos. Esperado {list(template)}; real {list(value)}")
        for key in template:
            if key in value:
                check_shape(value[key], template[key], f"{path}.{key}", report)
    elif isinstance(template, list):
        if not isinstance(value, list):
            report.error(f"{path}: se esperaba array (valor actual: {str(value)[:60]!r})")
            return
        for index, item in enumerate(value):
            check_shape(item, template[0] if template else {}, f"{path}[{index}]", report)
    else:
        if not isinstance(value, str):
            report.error(f"{path}: se esperaba string")
        elif not value.strip():
            if not path.endswith("For other, indicate"):
                report.error(f"{path}: cadena vacía; usa el marcador o completa el valor")
        elif TODO in value:
            report.error(f"{path}: queda un {TODO} sin completar")
        elif value.strip() in {"...", "N/A", "null", "None"}:
            report.error(f"{path}: valor de relleno no permitido")


def check_enums(data: dict, options: dict, report: Report) -> None:
    technical = data.get("TECHNICAL DATA", {})
    if technical.get("Visibility") not in (None, MARKER) and technical.get("Visibility") not in options["Visibility"]:
        report.error(f"TECHNICAL DATA.Visibility: {technical.get('Visibility')!r} fuera de {options['Visibility']}")
    if technical.get("Visibility") != "Public":
        report.error("TECHNICAL DATA.Visibility: debe ser 'Public' (toda librería standalone Tipo B es pública entre DUs)")
    if technical.get("Library Type") not in (None, MARKER) and technical.get("Library Type") not in options["Library Type"]:
        report.error(f"TECHNICAL DATA.Library Type: {technical.get('Library Type')!r} fuera de {options['Library Type']}")
    for method in data.get("EXECUTE - METHODS SUMMARY", []):
        for row in method.get("Accessed libraries", []) + method.get("Other accesses", []):
            country = row.get("Country")
            if country not in (None, MARKER) and country not in options["Country"]:
                report.error(f"{method.get('Method name')}: Country {country!r} fuera de {options['Country']}")
        for row in method.get("Other accesses", []):
            access_type = row.get("Access Type")
            if access_type not in (None, MARKER) and access_type not in options["Access Type"]:
                report.error(f"{method.get('Method name')}: Access Type {access_type!r} fuera de {options['Access Type']}")
        for section in ("Input Parameters", "Output Parameters"):
            for row in method.get("PARAMETERS", {}).get(section, []):
                fmt = row.get("Format Type")
                if fmt not in (None, MARKER) and fmt not in options["Format Type"]:
                    report.error(f"{method.get('Method name')}.{section}.{row.get('Name of APX field')}: Format Type {fmt!r} fuera de {options['Format Type']}")
                mandatory = row.get("Mandatory?")
                if mandatory not in (None,) and mandatory not in options["Mandatory?"]:
                    report.error(f"{method.get('Method name')}.{section}.{row.get('Name of APX field')}: Mandatory? {mandatory!r} fuera de {options['Mandatory?']}")


def check_methods(data: dict, root: Path, report: Report) -> None:
    library = find_library(root)
    expected_methods = [m.name for m in list_interface_methods(library.interface_java)]
    actual_blocks = data.get("EXECUTE - METHODS SUMMARY", [])
    actual_methods = [m.get("Method name") for m in actual_blocks if isinstance(m, dict)]
    if actual_methods != expected_methods:
        report.error(
            f"EXECUTE - METHODS SUMMARY: métodos distintos o en distinto orden que la interfaz. "
            f"Esperado {expected_methods}; real {actual_methods}"
        )

    if data.get("TECHNICAL DATA", {}).get("Library Identifier") != library.library_id:
        report.error(f"TECHNICAL DATA.Library Identifier: esperado {library.library_id!r}")

    impl_source = read_text(library.impl_java)
    for block in actual_blocks:
        if not isinstance(block, dict):
            continue
        name = block.get("Method name")
        spans = [(s, e) for n, s, e in method_spans(impl_source) if n == name]
        if not spans:
            report.error(f"{name}: no se encontró implementación en {library.impl_java}")
            continue
        start, end = spans[0]
        graph = build_graph_for_method(root, library.impl_java, name)

        libs = set(library_calls_in_text(impl_source[start:end]))
        for path, _, s, e in graph.methods:
            if path != library.impl_java:
                libs |= set(library_calls_in_text(read_text(path)[s:e]))
        expected_libs = sorted(libs)
        actual_libs = [(x.get("Library Identifier"), x.get("Method")) for x in block.get("Accessed libraries", []) if isinstance(x, dict)]
        if sorted(actual_libs) != expected_libs:
            report.error(f"{name}.Accessed libraries: esperado {expected_libs} (getServiceLibrary + llamadas alcanzables); real {sorted(actual_libs)}")

        expected_order = graph.first_emission_order()
        errors = block.get("Error Management", [])
        codes = [e.get("Error Code") for e in errors if isinstance(e, dict)]
        for code in {c for c in codes if codes.count(c) > 1}:
            report.error(f"{name}.Error Management: código duplicado {code}")
        for code in codes:
            if code not in expected_order:
                report.error(f"{name}.Error Management: {code} no se emite en ningún método alcanzable desde {name}() según el grafo")
            elif not CODE.match(code or ""):
                report.warn(f"{name}.Error Management: código con formato inusual {code!r}")
        for code in expected_order:
            if code not in codes:
                report.warn(f"{name}.Error Management: OMISIÓN de {code}, emitido en el grafo alcanzable; inclúyelo salvo que demuestres que nunca llega como advice de la librería")
        common = [c for c in codes if c in expected_order]
        if common != [c for c in expected_order if c in codes]:
            report.error(f"{name}.Error Management: orden {common} distinto del orden DFS de primera emisión {[c for c in expected_order if c in codes]}")
        for entry in errors if isinstance(errors, list) else []:
            code = entry.get("Error Code", "")
            candidates = {e.description for e in graph.emissions if e.code == code and e.description and not e.description.startswith("[log")}
            description = entry.get("Description of the error situation", "")
            if candidates and normalize(description) not in {normalize(c) for c in candidates}:
                report.warn(f"{name}.Error Management.{code}: descripción {description!r} distinta de las candidatas del código {sorted(candidates)}")


def check_parameters(data: dict, report: Report) -> None:
    for block in data.get("EXECUTE - METHODS SUMMARY", []):
        if not isinstance(block, dict):
            continue
        name = block.get("Method name")
        for section in ("Input Parameters", "Output Parameters"):
            for row in block.get("PARAMETERS", {}).get(section, []):
                if not isinstance(row, dict):
                    continue
                description = row.get("Description", "")
                if TAUTOLOGY.search(description or ""):
                    report.error(f"{name}.{section}.{row.get('Name of APX field')}: descripción tautológica/generada: {description!r}")
                if not row.get("Name of APX field", "").strip():
                    report.error(f"{name}.{section}: fila sin 'Name of APX field'")


def check_descriptions(data: dict, report: Report) -> None:
    for block in data.get("EXECUTE - METHODS SUMMARY", []):
        if not isinstance(block, dict):
            continue
        name = block.get("Method name")
        for key in ("Brief description", "DESCRIPTION OF THE FUNCTIONALITY"):
            value = block.get(key, "")
            if TAUTOLOGY.search(value or ""):
                report.error(f"{name}.{key}: descripción tautológica/generada: {value!r}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    root, path = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    report = Report()

    data, load_errors = load_json_strict(path)
    for message in load_errors:
        report.error(message)
    if isinstance(data, dict):
        check_shape(data, load_contract_template(), "$", report)
        check_enums(data, load_options(), report)
        check_methods(data, root, report)
        check_parameters(data, report)
        check_descriptions(data, report)
        text = json.dumps(data, ensure_ascii=False)
        print(f"Marcadores '{MARKER}': {text.count(MARKER)}")

    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"AVISO: {message}")
    print(f"RESULTADO {path.stem}: {'OK' if not report.errors else 'FALLA'} ({len(report.errors)} errores, {len(report.warnings)} avisos)")
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
