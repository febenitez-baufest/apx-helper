"""Valida un contrato de transacción APX generado contra el contrato, el XML y el código.

Uso: python validate.py <raiz_proyecto> <contrato_generado.json> [<ID_TRANSACCION>]

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

from apx_common import (  # noqa: E402
    ENUMS,
    MARKER,
    SEVERITY_MAP,
    TODO,
    Module,
    canonical_rows,
    contract_path,
    explicit_markers,
    java_index,
    library_calls,
    load_json_strict,
    method_spans,
    normalize,
    read_text,
    strip_code,
    xml_root,
    xml_section,
)
from callgraph import build_graph  # noqa: E402

TAUTOLOGY = re.compile(
    r"Return value for|Set value for|The execute method|input parameter \w+$|output parameter \w+$|^The \w+ class",
    re.IGNORECASE,
)
OMISSION = re.compile(r"not assigned|no asignad|not returned|no devuelt|without response|sin respuesta|no se asigna", re.IGNORECASE)
CODE = re.compile(r"^[A-Z0-9]{4}\d{8}$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


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
            report.error(f"{path}: cadena vacía; usa el marcador")
        elif TODO in value:
            report.error(f"{path}: queda un {TODO} sin completar")
        elif value.strip() in {"...", "N/A", "null", "None"}:
            report.error(f"{path}: valor de relleno no permitido")
        key = path.rsplit(".", 1)[-1]
        if key in ENUMS and isinstance(value, str) and value not in ENUMS[key]:
            report.error(f"{path}: valor {value!r} fuera de la lista permitida")


def nontrivial_accessors(root: Path, class_name: str) -> set[str]:
    """Campos (en minúscula inicial) cuyo getter o setter contiene lógica en el DTO."""
    fields = set()
    trivial = re.compile(r"^\{\s*(?:return\s+(?:this\.)?\w+\s*;|(?:this\.)?\w+\s*=\s*\w+\s*;)?\s*\}$")
    for path in java_index(root).get(class_name, []):
        text = read_text(path)
        clean = strip_code(text)
        for name, start, end in method_spans(text):
            accessor = re.match(r"(?:get|set|is)([A-Z]\w*)", name)
            if accessor and not trivial.match(re.sub(r"\s+", " ", clean[clean.find("{", start):end])):
                fields.add(accessor.group(1)[:1].lower() + accessor.group(1)[1:])
    return fields


def check_references(data: dict, module: Module, root: Path, report: Report) -> None:
    """Columnas/constantes y rutas de parámetros citadas en el texto deben existir."""
    corpus = "\n".join(
        read_text(p) for p in (root / "artifact").rglob("*") if p.suffix in {".java", ".properties", ".xml", ".sql"} and "target" not in p.parts
    )
    known = set(re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", corpus))
    xml = xml_root(module)
    paths = {r["Name of APX field"] for s in ("paramsIn", "paramsOut") for r in canonical_rows(xml_section(xml, s))}
    roots = {p.split(".")[0] for p in paths}
    texts = [("EXECUTION FLOWS", data.get("EXECUTION FLOWS - DETAILED DESCRIPTION", ""))]
    texts += [(f"Accessed Libraries.{x.get('Method')}", x.get("Description", "")) for x in data.get("TECHNICAL DATA", {}).get("Accessed Libraries", [])]
    for key in ("Input Parameters", "Output Parameters"):
        texts += [(f"{key}.{r.get('Name of APX field')}", r.get("Description", "")) for r in data.get("PARAMETERS", {}).get(key, [])]
    for where, text in texts:
        if not isinstance(text, str) or text == MARKER:
            continue
        for token in set(re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", text)) - known:
            report.error(f"{where}: cita '{token}', que no existe en el código ni en los recursos del proyecto")
        for path in set(re.findall(r"\b([a-z]\w*(?:\.[a-z]\w*)+)\b", text)):
            if path.split(".")[0] in roots and path not in paths:
                report.warn(f"{where}: cita la ruta '{path}', que no es un parámetro del XML (¿entrada/salida confundidas?)")


def check_parameters(data: dict, module: Module, report: Report) -> None:
    xml = xml_root(module)
    for section, key in (("paramsIn", "Input Parameters"), ("paramsOut", "Output Parameters")):
        canon = canonical_rows(xml_section(xml, section))
        packages = {r["Name of APX field"]: r["_package"].rsplit(".", 1)[-1] for r in canon if r["_package"]}
        for row in data.get("PARAMETERS", {}).get(key, []) if key == "Output Parameters" else []:
            name = row.get("Name of APX field", "")
            parent, _, leaf = name.rpartition(".")
            owner = packages.get(parent)
            if owner and re.search(r"without transformation", row.get("Description", ""), re.I) and leaf in nontrivial_accessors(module.root, owner):
                report.error(f"{key}.{name}: dice 'without transformation' pero {owner} tiene getter/setter con lógica para '{leaf}' (sección 8 del expediente); describe la transformación")
        expected = [(r["Name of APX field"], r["Mandatory?"], r["APX data type"]) for r in canonical_rows(xml_section(xml, section))]
        actual = [
            (r.get("Name of APX field"), r.get("Mandatory?"), r.get("APX data type"))
            for r in data.get("PARAMETERS", {}).get(key, []) if isinstance(r, dict)
        ]
        if expected != actual:
            diff = next((i for i, (a, b) in enumerate(zip(expected, actual)) if a != b), min(len(expected), len(actual)))
            exp = expected[diff] if diff < len(expected) else "<fin>"
            act = actual[diff] if diff < len(actual) else "<fin>"
            report.error(f"{key}: no coincide con el XML (esperadas {len(expected)}, reales {len(actual)}); fila {diff + 1}: esperado {exp}, real {act}")
        for row in data.get("PARAMETERS", {}).get(key, []):
            description = row.get("Description", "") if isinstance(row, dict) else ""
            if TAUTOLOGY.search(description):
                report.error(f"{key}.{row.get('Name of APX field')}: descripción tautológica/generada: {description!r}")
            if key == "Output Parameters" and OMISSION.search(description):
                report.warn(f"{key}.{row.get('Name of APX field')}: afirma omisión de salida; confirma una guarda antes de la operación APX final: {description!r}")


def check_technical(data: dict, module: Module, root: Path, report: Report) -> None:
    technical = data.get("TECHNICAL DATA", {})
    xml = xml_root(module)
    for key, attr in (("Country", "country"), ("Version", "version"), ("Transaction Identifier", "transactionName")):
        if xml.get(attr) and technical.get(key) != xml.get(attr):
            report.error(f"TECHNICAL DATA.{key}: {technical.get(key)!r} distinto del XML {xml.get(attr)!r}")

    expected_libs = library_calls(module.concrete[0])
    actual_libs = [(x.get("Library Identifier"), x.get("Method")) for x in technical.get("Accessed Libraries", []) if isinstance(x, dict)]
    if actual_libs != expected_libs:
        report.error(f"Accessed Libraries: esperado {expected_libs} (getServiceLibrary + llamadas, orden lexicográfico); real {actual_libs}")

    graph = build_graph(root, module.concrete[0])
    reachable = sorted({p for p, *_ in graph.methods})
    expected_order = graph.first_emission_order()

    errors = technical.get("Error Management", [])
    codes = [e.get("Error Code") for e in errors if isinstance(e, dict)]
    for code in {c for c in codes if codes.count(c) > 1}:
        report.error(f"Error Management: código duplicado {code}")
    extra = [c for c in codes if c not in expected_order]
    missing = [c for c in expected_order if c not in codes]
    for code in extra:
        report.error(f"Error Management: {code} no se emite en ningún método alcanzable desde execute() según el grafo")
    for code in missing:
        report.warn(f"Error Management: OMISIÓN de {code}, emitido en el grafo alcanzable; inclúyelo salvo que demuestres que nunca llega como advice")
    common = [c for c in codes if c in expected_order]
    if common != [c for c in expected_order if c in codes]:
        report.error(f"Error Management: orden {common} distinto del orden DFS de primera emisión {[c for c in expected_order if c in codes]}")
    severities_used = {e.code for e in graph.emissions if e.kind == "severity"}
    for entry in errors if isinstance(errors, list) else []:
        code = entry.get("Error Code", "")
        if not CODE.match(code or ""):
            report.warn(f"Error Management: código con formato inusual {code!r}")
        severity = entry.get("Severity")
        valid = {SEVERITY_MAP[s] for s in severities_used if s in SEVERITY_MAP}
        if severity != MARKER and valid and severity not in valid:
            report.error(f"Error Management.{code}: severidad {severity!r} no corresponde a ningún setSeverity alcanzable ({sorted(severities_used)})")
        if severity == MARKER and valid:
            report.warn(f"Error Management.{code}: severidad marcador pero el flujo usa {sorted(severities_used)}; confirma que ningún setSeverity alcanza este advice")
        candidates = {e.description for e in graph.emissions if e.code == code and e.description and not e.description.startswith("[log")}
        description = entry.get("Description of the error situation", "")
        if candidates and normalize(description) not in {normalize(c) for c in candidates}:
            report.warn(f"Error Management.{code}: descripción {description!r} distinta de las del código {sorted(candidates)}")

    markers = explicit_markers(root, module, reachable)
    flow = data.get("EXECUTION FLOWS - DETAILED DESCRIPTION", "")
    for code in codes:
        if code and code not in flow:
            report.error(f"EXECUTION FLOWS: no menciona el código {code} ni su condición de disparo")
    for library, method in expected_libs:
        if method not in flow:
            report.error(f"EXECUTION FLOWS: no menciona {library}.{method}")
    labels = re.findall(r"(?:^|\s)([1-5])\.\s", flow)
    if labels[:5] != ["1", "2", "3", "4", "5"]:
        report.warn("EXECUTION FLOWS: no usa las cinco etiquetas numeradas 1.-5. en orden")
    for key, kind in (("Transactional?", "transactional"), ("Asynchronous?", "async")):
        if technical.get(key) in {"Yes", "No"} and not markers[kind]:
            report.error(f"TECHNICAL DATA.{key}: {technical.get(key)!r} sin evidencia explícita en el código/configuración; usa el marcador")
    for key, kind in (("Asynchronous Consumers", "async"), ("Events to which it is subscribed", "async")):
        if technical.get(key) and not markers[kind]:
            report.error(f"TECHNICAL DATA.{key}: elementos sin listener/consumer explícito")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        return 2
    root, path = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    tx_id = sys.argv[3] if len(sys.argv) == 4 else path.stem
    module = Module(root, tx_id)
    report = Report()

    data, load_errors = load_json_strict(path)
    for message in load_errors:
        report.error(message)
    if isinstance(data, dict):
        template = json.loads(contract_path(root).read_text(encoding="utf-8"))
        check_shape(data, template, "$", report)
        check_parameters(data, module, report)
        check_technical(data, module, root, report)
        check_references(data, module, root, report)
        text = json.dumps(data, ensure_ascii=False)
        print(f"Marcadores '{MARKER}': {text.count(MARKER)}")

    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"AVISO: {message}")
    print(f"RESULTADO {tx_id}: {'OK' if not report.errors else 'FALLA'} ({len(report.errors)} errores, {len(report.warnings)} avisos)")
    return 0 if not report.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
