"""Utilidades compartidas para analizar transacciones APX du_online (solo stdlib)."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

MARKER = "NO HAY INFORMACIÓN SUFICIENTE"
TODO = "__TODO__"
TYPE_MAP = {"String": "string", "Long": "long", "Double": "double", "Boolean": "boolean"}
SEVERITY_MAP = {
    "WARN": "04 - WARNING",
    "WRN": "04 - WARNING",
    "ENR": "06 - ERROR NO ROLLBACK",
    "ERR": "08 - ERROR WITH ROLLBACK",
    "EWR": "08 - ERROR WITH ROLLBACK",
}
ENUMS = {
    "Country": {"ES", "MX", "PE", "CO", "US", "GL", "AR", "Common"},
    "Asynchronous?": {"Yes", "No", MARKER},
    "Transactional?": {"Yes", "No", MARKER},
    "Severity": set(SEVERITY_MAP.values()) | {MARKER},
    "APX data type": {"compound", "double", "long", "string", "file", "date", "boolean", "dto", MARKER},
    "Mandatory?": {"Yes", "No"},
}
EXPLICIT_TX_PATTERNS = re.compile(
    r"@Transactional|TransactionTemplate|PlatformTransactionManager|\.commit\(|\.rollback\(|tx:annotation-driven|tx:advice"
)
EXPLICIT_ASYNC_PATTERNS = re.compile(
    r"@Async|@EventListener|@JmsListener|@KafkaListener|ApplicationListener|ExecutorService|CompletableFuture|new Thread\("
)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class Module:
    """Rutas de una transacción dentro del proyecto."""

    def __init__(self, root: Path, tx_id: str) -> None:
        self.root = root
        self.tx_id = tx_id
        self.dir = root / "artifact" / "transactions" / tx_id
        self.xml = self.dir / "src" / "main" / "resources" / f"{tx_id}.xml"
        self.pom = self.dir / "pom.xml"
        java = sorted((self.dir / "src" / "main" / "java").rglob("*Transaction.java"))
        self.abstract = [p for p in java if p.name.startswith("Abstract")]
        self.concrete = [p for p in java if not p.name.startswith("Abstract")]


def list_transactions(root: Path) -> list[str]:
    base = root / "artifact" / "transactions"
    return sorted(p.name for p in base.iterdir() if p.is_dir() and (p / "pom.xml").exists())


def contract_path(root: Path) -> Path:
    for candidate in (root / "contrato" / "contrato-transaccion.json", root.parent / "contrato" / "contrato-transaccion.json"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No se encontró contrato/contrato-transaccion.json")


@lru_cache(maxsize=None)
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------- XML

def xml_root(module: Module) -> ET.Element:
    return ET.parse(module.xml).getroot()


def ordered_children(element: ET.Element) -> list[ET.Element]:
    children = [c for c in element if local(c.tag) in {"parameter", "dto", "list", "file", "date"}]
    if children and all(c.get("order") is not None for c in children):
        return sorted(children, key=lambda c: int(c.get("order", "0")))
    return children


def apx_type(element: ET.Element) -> str:
    tag = local(element.tag)
    if tag in {"dto", "file", "date"}:
        return tag
    if tag == "list":
        return "compound"
    xml_type = element.get("type", "").strip()
    if xml_type.startswith("Date"):
        return "date"
    return TYPE_MAP.get(xml_type, MARKER)


def canonical_rows(container: ET.Element | None) -> list[dict[str, str]]:
    """Filas canónicas: omite <dto name="Type"> hijo de <list>, conserva <parameter name="Type">."""
    rows: list[dict[str, str]] = []
    if container is None:
        return rows

    def visit(element: ET.Element, path: tuple[str, ...], parent_tag: str) -> None:
        tag = local(element.tag)
        name = element.get("name", "")
        technical = tag == "dto" and name == "Type" and parent_tag == "list"
        current = path if technical else path + (name,)
        if technical and rows and rows[-1]["Name of APX field"] == ".".join(path):
            rows[-1]["_package"] = element.get("package", "")
        if not technical:
            rows.append({
                "Name of APX field": ".".join(current),
                "Mandatory?": {"1": "Yes", "0": "No"}.get(element.get("mandatory", ""), MARKER),
                "APX data type": apx_type(element),
                "_package": element.get("package", ""),
            })
        for child in ordered_children(element):
            visit(child, current, tag)

    for child in ordered_children(container):
        visit(child, (), local(container.tag))
    return rows


def xml_section(root: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in root if local(c.tag) == name), None)


def functional_description(module: Module) -> str:
    root = xml_root(module)
    parts = [normalize(next((c.text for c in root if local(c.tag) == "description"), ""))]
    pom = ET.parse(module.pom).getroot()
    parts.append(normalize(next((c.text for c in pom if local(c.tag) == "description"), "")))
    result: list[str] = []
    for part in parts:
        if part and part not in result:
            result.append(part)
    return " ".join(result) or MARKER


# ---------------------------------------------------------------- Java

@lru_cache(maxsize=None)
def strip_code(source: str) -> str:
    """Reemplaza comentarios y literales por espacios conservando posiciones."""
    out = list(source)
    i, n = 0, len(source)
    while i < n:
        two = source[i:i + 2]
        if two == "//":
            j = source.find("\n", i)
            j = n if j < 0 else j
            out[i:j] = " " * (j - i)
            i = j
        elif two == "/*":
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out[i:j] = [c if c == "\n" else " " for c in source[i:j]]
            i = j
        elif source[i] in "\"'":
            quote, j = source[i], i + 1
            while j < n and source[j] != quote:
                j += 2 if source[j] == "\\" else 1
            j = min(j + 1, n)
            out[i + 1:j - 1] = " " * max(0, j - i - 2)
            i = j
        else:
            i += 1
    return "".join(out)


@lru_cache(maxsize=None)
def method_spans(source: str) -> tuple[tuple[str, int, int], ...]:
    """(nombre, inicio, fin) de cada método con cuerpo."""
    clean = strip_code(source)
    spans = []
    pattern = re.compile(r"(?:public|protected|private|static|final|synchronized|\s)+[\w<>\[\], ?]+\s+(\w+)\s*\([^;{)]*\)\s*(?:throws [\w., ]+)?\{")
    for match in pattern.finditer(clean):
        name = match.group(1)
        if name in {"if", "for", "while", "switch", "catch", "return", "new"}:
            continue
        depth, j = 0, match.end() - 1
        while j < len(clean):
            if clean[j] == "{":
                depth += 1
            elif clean[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        spans.append((name, match.start(), j + 1))
    return tuple(spans)


def line_of(source: str, index: int) -> int:
    return source.count("\n", 0, index) + 1


def numbered(source: str, start: int, end: int) -> str:
    first = line_of(source, start)
    lines = source[source.rfind("\n", 0, start) + 1:end].splitlines()
    return "\n".join(f"{first + k:5d}| {line}" for k, line in enumerate(lines))


def method_block(path: Path, name: str) -> list[tuple[int, int, str]]:
    source = read_text(path)
    return [(line_of(source, s), line_of(source, e), numbered(source, s, e)) for m, s, e in method_spans(source) if m == name]


def library_calls(concrete: Path) -> list[tuple[str, str]]:
    source = strip_code(read_text(concrete))
    variables = dict(
        (var, lib) for var, lib in re.findall(r"(\w+)\s*=\s*(?:this\.)?getServiceLibrary\(\s*(\w+)\.class\s*\)", source)
    )
    calls = set()
    for var, lib in variables.items():
        for method in re.findall(rf"\b{re.escape(var)}\.(\w+)\s*\(", source):
            calls.add((lib, method))
    for lib, method in re.findall(r"getServiceLibrary\(\s*(\w+)\.class\s*\)\s*\.(\w+)\s*\(", source):
        calls.add((lib, method))
    return sorted(calls)


@lru_cache(maxsize=None)
def java_index(root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = {}
    for path in (root / "artifact").rglob("*.java"):
        parts = path.parts
        if "src" in parts and "main" in parts and "target" not in parts:
            index.setdefault(path.stem, []).append(path)
    return index


@lru_cache(maxsize=None)
def constants(root: Path) -> dict[str, str]:
    """Constantes String indexadas como 'Clase.NOMBRE'."""
    values: dict[str, str] = {}
    pattern = re.compile(r"(?:static\s+final|final\s+static)\s+String\s+(\w+)\s*=\s*\"([^\"]*)\"")
    for class_name, paths in java_index(root).items():
        for path in paths:
            for name, value in pattern.findall(read_text(path)):
                values.setdefault(f"{class_name}.{name}", value)
    return values


def library_files(root: Path, library: str) -> tuple[Path | None, Path | None]:
    index = java_index(root)
    interface = next((p for p in index.get(library, []) if "libraries" in p.parts), None)
    impl = next((p for p in index.get(f"{library}Impl", []) if "libraries" in p.parts), None)
    return interface, impl


def referenced_classes(root: Path, start: list[Path], depth: int = 4) -> list[Path]:
    """Clausura de clases del proyecto referenciadas por nombre simple (excluye DTOs)."""
    index = java_index(root)
    seen: list[Path] = []
    frontier = list(start)
    for _ in range(depth):
        nxt = []
        for path in frontier:
            if path in seen:
                continue
            seen.append(path)
            for name in set(re.findall(r"\b([A-Z]\w+)\b", strip_code(read_text(path)))):
                for candidate in index.get(name, []):
                    if "dtos" not in candidate.parts and candidate not in seen:
                        nxt.append(candidate)
        frontier = nxt
    return seen


def resolve_code(expression: str, root: Path, owner: Path | None = None) -> str:
    """Resuelve un literal o constante: Clase.NOMBRE, o NOMBRE en la clase actual, import estático o único."""
    expression = expression.strip()
    literal = re.fullmatch(r"\"([^\"]*)\"", expression)
    if literal:
        return literal.group(1)
    table = constants(root)
    parts = expression.split(".")
    if len(parts) >= 2 and f"{parts[-2]}.{parts[-1]}" in table:
        return table[f"{parts[-2]}.{parts[-1]}"]
    name = parts[-1]
    if owner is not None:
        own = table.get(f"{owner.stem}.{name}")
        if own is not None:
            return own
        imported = re.search(rf"import\s+static\s+[\w.]*\.(\w+)\.{name}\s*;", read_text(owner))
        if imported and f"{imported.group(1)}.{name}" in table:
            return table[f"{imported.group(1)}.{name}"]
    matches = {v for k, v in table.items() if k.endswith(f".{name}")}
    return matches.pop() if len(matches) == 1 else f"?{expression}"


def explicit_markers(root: Path, module: Module, files: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {"transactional": [], "async": []}
    candidates = list(files) + list((module.dir / "src" / "main").rglob("*.xml"))
    for path in candidates:
        text = strip_code(read_text(path)) if path.suffix == ".java" else read_text(path)
        for number, line in enumerate(text.splitlines(), 1):
            if EXPLICIT_TX_PATTERNS.search(line):
                found["transactional"].append(f"{path}:{number}: {line.strip()}")
            if EXPLICIT_ASYNC_PATTERNS.search(line):
                found["async"].append(f"{path}:{number}: {line.strip()}")
    return found


def load_json_strict(path: Path) -> tuple[object | None, list[str]]:
    raw = path.read_bytes()
    errors = []
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("El archivo tiene BOM UTF-8")
        raw = raw[3:]
    text = raw.decode("utf-8")
    try:
        value, end = json.JSONDecoder().raw_decode(text.lstrip())
    except json.JSONDecodeError as exc:
        return None, errors + [f"JSON inválido: {exc}"]
    if text.lstrip()[end:].strip():
        errors.append("Hay contenido adicional después del primer objeto JSON (objetos concatenados)")
    return value, errors
