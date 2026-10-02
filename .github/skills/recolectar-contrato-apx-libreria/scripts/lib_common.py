"""Utilidades compartidas para analizar librerías APX standalone (apx.json: resource_type "lib").

Reutiliza las primitivas de texto/Java de la skill de transacciones (strip_code, method_spans,
etc., que no asumen ninguna estructura de carpetas) pero reimplementa el índice de clases, las
constantes y el grafo de llamadas porque una librería no vive bajo `artifact/`: la interfaz y la
implementación están en la raíz del proyecto (`<UUAARXXX>/`, `<UUAARXXX>IMPL/`).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_TX_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "recolectar-contrato-apx" / "scripts"
sys.path.insert(0, str(_TX_SCRIPTS))

from apx_common import (  # noqa: E402
    MARKER,
    TODO,
    line_of,
    load_json_strict,
    normalize,
    numbered,
    read_text,
    strip_code,
    method_spans,
)

PRIMITIVE_FORMAT = {
    "String": "string", "CharSequence": "string",
    "Long": "long", "long": "long",
    "Integer": "int", "int": "int",
    "Double": "double", "double": "double",
    "Float": "float", "float": "float",
    "Boolean": "boolean", "boolean": "boolean",
    "Byte": "byte", "byte": "byte",
    "Character": "char", "char": "char",
    "Short": "short", "short": "short",
    "Date": "date", "LocalDate": "date", "LocalDateTime": "date", "Calendar": "date",
}
ACCESS_TYPE_BEANS = [
    (re.compile(r"\bJdbcTemplate\b|\bDataSource\b"), "JDBC"),
    (re.compile(r"\bMongoTemplate\b|\bMongoClient\b"), "MongoDB"),
    (re.compile(r"\bCouchbaseTemplate\b|\bCouchbaseConnector\b|CouchbaseCluster"), "Document Manager"),
    (re.compile(r"factory-method\s*=\s*\"getAPIConnector\"|internalApiConnector|\bAPIConnector\b"), "Proxy Service"),
    (re.compile(r"osgi:reference[^>]*interface=\"[^\"]*Proxy[^\"]*\""), "Proxy Service"),
    (re.compile(r"\bNeo4jTemplate\b|\bNeo4jClient\b"), "Neo4j"),
    (re.compile(r"\bIMSConnect\b"), "IMSConnect"),
    (re.compile(r"\bEntityManager\b|\bJpaRepository\b"), "JPA"),
    (re.compile(r"RulesEngine|DroolsTemplate"), "Rules Engine"),
]
TAUTOLOGY = re.compile(
    r"Return value for|Set value for|The execute method|input parameter \w+$|output parameter \w+$"
    r"|^The \w+ class|^(El|La) (m[eé]todo|clase) \w+$",
    re.IGNORECASE,
)
CODE = re.compile(r"^[A-Z0-9]{4}\d{8}$")

IGNORED_DIR_SEGMENTS = {"target", ".git", "node_modules"}


def is_tautological(text: str, method_name: str = "") -> bool:
    """True si el texto solo repite el nombre del método/clase sin aportar significado (p. ej.
    Javadoc autogenerado como "El método executeX" o "The executeX method")."""
    normalized = normalize(text)
    if not normalized:
        return True
    if TAUTOLOGY.search(normalized):
        return True
    if method_name and re.fullmatch(rf"(?:El|La|The)?\s*(?:m[eé]todo|method)?\s*{re.escape(method_name)}\.?", normalized, re.IGNORECASE):
        return True
    return False


@dataclass
class Method:
    name: str
    params: list[tuple[str, str]]  # (java_type, param_name)
    return_type: str
    javadoc: str
    start: int
    end: int


@dataclass
class Library:
    root: Path
    library_id: str
    interface_dir: Path
    impl_dir: Path
    interface_java: Path
    impl_java: Path
    abstract_java: Path | None
    pom_interface: Path
    pom_impl: Path
    pom_parent: Path
    arc_xmls: list[Path]
    multilanguage: Path | None


def _iter_java(root: Path):
    for path in root.rglob("*.java"):
        if not any(part in IGNORED_DIR_SEGMENTS for part in path.parts):
            yield path


@lru_cache(maxsize=None)
def java_index(root: Path) -> dict[str, list[Path]]:
    """Clases del propio proyecto indexadas por nombre simple (toda la raíz, sin asumir `artifact/`)."""
    index: dict[str, list[Path]] = {}
    for path in _iter_java(root):
        index.setdefault(path.stem, []).append(path)
    return index


@lru_cache(maxsize=None)
def constants(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    pattern = re.compile(r"(?:static\s+final|final\s+static)\s+String\s+(\w+)\s*=\s*\"([^\"]*)\"")
    for class_name, paths in java_index(root).items():
        for path in paths:
            for name, value in pattern.findall(read_text(path)):
                values.setdefault(f"{class_name}.{name}", value)
    return values


def resolve_code(expression: str, root: Path, owner: Path | None = None) -> str:
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


def find_library(root: Path) -> Library:
    """Localiza la interfaz y la implementación de una librería Tipo B a partir de su raíz."""
    skip = {".git", ".github", "target", "doc", "com"}
    candidates = [
        p for p in root.iterdir()
        if p.is_dir() and p.name not in skip and not p.name.endswith("IMPL") and (p / "pom.xml").exists()
    ]
    interface_dir = next((p for p in candidates if (p / "src" / "main" / "java").exists()), None)
    if interface_dir is None:
        raise SystemExit(f"No se encontró la carpeta de interfaz de la librería bajo {root}")
    library_id = interface_dir.name
    impl_dir = root / f"{library_id}IMPL"
    if not impl_dir.exists():
        raise SystemExit(f"No se encontró la carpeta de implementación {impl_dir}")
    interface_matches = list((interface_dir / "src" / "main" / "java").rglob(f"{library_id}.java"))
    impl_matches = list((impl_dir / "src" / "main" / "java").rglob(f"{library_id}Impl.java"))
    abstract_matches = list((impl_dir / "src" / "main" / "java").rglob(f"{library_id}Abstract.java"))
    if len(interface_matches) != 1:
        raise SystemExit(f"{library_id}: se esperaba exactamente un {library_id}.java, encontrados {interface_matches}")
    if len(impl_matches) != 1:
        raise SystemExit(f"{library_id}: se esperaba exactamente un {library_id}Impl.java, encontrados {impl_matches}")
    arc_xmls = sorted((impl_dir / "src" / "main" / "resources").rglob("*-arc.xml"))
    multilanguage = next(iter((impl_dir / "src" / "main" / "resources").rglob("multilanguage-ES.properties")), None)
    return Library(
        root=root,
        library_id=library_id,
        interface_dir=interface_dir,
        impl_dir=impl_dir,
        interface_java=interface_matches[0],
        impl_java=impl_matches[0],
        abstract_java=abstract_matches[0] if abstract_matches else None,
        pom_interface=interface_dir / "pom.xml",
        pom_impl=impl_dir / "pom.xml",
        pom_parent=root / "pom.xml",
        arc_xmls=arc_xmls,
        multilanguage=multilanguage,
    )


def pom_description(pom: Path) -> str:
    if not pom.exists():
        return ""
    match = re.search(r"<description>(.*?)</description>", read_text(pom), re.S)
    return normalize(match.group(1)) if match else ""


def library_type_from_pom(library: Library) -> str:
    """Solo cuenta el uso real en <dependencies> del propio módulo (impl + interfaz), nunca
    la mera declaración de propiedades en el POM agregador, que suele listar ambas por plantilla."""
    dependencies_text = ""
    for pom in (library.pom_impl, library.interface_dir / "pom.xml"):
        if not pom.exists():
            continue
        match = re.search(r"<dependencies>(.*?)</dependencies>", read_text(pom), re.S)
        if match:
            dependencies_text += match.group(1)
    online = bool(re.search(r"\$\{apx\.core\.online\.version\}|elara-online", dependencies_text))
    batch = bool(re.search(r"\$\{apx\.core\.batch\.version\}|elara-batch", dependencies_text))
    if online and batch:
        return "Both"
    if online:
        return "On-line"
    if batch:
        return "Batch"
    return MARKER


def javadoc_before(source: str, index: int) -> str:
    """Javadoc completo (todas las líneas `*`, incluidos `@param`/`@return`) inmediatamente anterior."""
    before = source[:index].rstrip()
    if before.endswith("*/"):
        start = before.rfind("/**")
        if start >= 0:
            return re.sub(r"\s*\n\s*\*\s?", " ", before[start + 3:-2]).strip()
    return ""


def javadoc_summary(javadoc: str) -> str:
    """Solo el texto descriptivo de un Javadoc: recorta a partir del primer `@tag` y limpia
    asteriscos huérfanos que quedan de líneas de Javadoc en blanco entre párrafos."""
    summary = re.split(r"\s@\w+", javadoc)[0]
    return normalize(re.sub(r"\s*\*\s*$", "", summary))


def _split_params(raw: str) -> list[tuple[str, str]]:
    raw = raw.strip()
    if not raw:
        return []
    params = []
    for part in re.split(r",(?![^<]*>)", raw):
        part = re.sub(r"@\w+(\([^)]*\))?\s*", "", part).strip()
        part = re.sub(r"\bfinal\s+", "", part)
        tokens = part.rsplit(" ", 1)
        if len(tokens) == 2:
            params.append((tokens[0].strip(), tokens[1].strip()))
    return params


def list_interface_methods(interface_java: Path) -> list[Method]:
    """Métodos públicos declarados por la interfaz, en orden de aparición."""
    source = read_text(interface_java)
    clean = strip_code(source)
    methods = []
    pattern = re.compile(r"(?:public\s+)?([\w<>\[\],.? ]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws [\w., ]+)?;")
    for match in pattern.finditer(clean):
        return_type, name, params_raw = match.group(1).strip(), match.group(2), match.group(3)
        if name in {"if", "for", "while", "switch", "catch"}:
            continue
        methods.append(Method(
            name=name,
            params=_split_params(source[match.start(3):match.end(3)]),
            return_type=return_type,
            javadoc=javadoc_before(source, match.start()),
            start=match.start(),
            end=match.end(),
        ))
    return methods


def format_type(java_type: str) -> str:
    java_type = java_type.strip().rstrip("...")
    if java_type.endswith("[]"):
        return "array"
    base = re.match(r"([\w.]+)(?:<(.+)>)?$", java_type)
    if not base:
        return MARKER
    raw = base.group(1).rsplit(".", 1)[-1]
    if raw in {"List", "Collection", "Iterable"}:
        return "list"
    if raw == "Set":
        return "set"
    if raw == "Queue" or raw == "Deque":
        return "queue"
    if raw == "Map":
        return "map"
    if raw in PRIMITIVE_FORMAT:
        return PRIMITIVE_FORMAT[raw]
    if raw in {"void", "Void"}:
        return ""
    if raw[:1].isupper():
        return "bean"
    return MARKER


def generic_arg(java_type: str) -> str | None:
    match = re.match(r"[\w.]+<(.+)>$", java_type.strip())
    return match.group(1).rsplit(".", 1)[-1].strip() if match else None


@lru_cache(maxsize=None)
def dto_source(root: Path, simple_name: str) -> Path | None:
    matches = [p for p in java_index(root).get(simple_name, [])]
    return matches[0] if matches else None


def dto_fields(root: Path, simple_name: str) -> list[tuple[str, str, str]]:
    """(nombre_campo, tipo_java, javadoc) de los campos privados declarados en el DTO, si su fuente está disponible."""
    path = dto_source(root, simple_name)
    if path is None:
        return []
    source = read_text(path)
    clean = strip_code(source)
    fields = []
    for match in re.finditer(r"(?m)^\s*private\s+(?!static)([\w<>\[\],. ]+?)\s+(\w+)\s*(?:=[^;]+)?;", clean):
        fields.append((match.group(2), match.group(1).strip(), javadoc_before(source, match.start())))
    return fields


def access_type_candidates(arc_xml: Path) -> list[tuple[str, str, str]]:
    """(Access Type, bean id, línea fuente) por cada `<bean>`/`<osgi:reference>` de infraestructura
    reconocido en *-arc.xml. Solo mira la línea que declara el bean (no las `<property ref="...">`
    que simplemente lo inyectan en otro bean), para no duplicar el mismo acceso."""
    if not arc_xml.exists():
        return []
    text = read_text(arc_xml)
    found: dict[str, tuple[str, str, str]] = {}
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not re.match(r"<(bean|osgi:reference)\b", stripped):
            continue
        for pattern, access_type in ACCESS_TYPE_BEANS:
            if pattern.search(line):
                bean = re.search(r'id="([^"]+)"', line)
                key = bean.group(1) if bean else stripped
                found.setdefault(key, (access_type, key, f"{arc_xml.name}:{number}: {stripped}"))
    return list(found.values())


def library_calls_in_text(text: str) -> list[tuple[str, str]]:
    """Mismas reglas que la skill de transacciones (getServiceLibrary + llamada) pero sobre un texto arbitrario."""
    clean = strip_code(text)
    variables = dict(
        (var, lib) for var, lib in re.findall(r"(\w+)\s*=\s*(?:this\.)?getServiceLibrary\(\s*(\w+)\.class\s*\)", clean)
    )
    calls = set()
    for var, lib in variables.items():
        for method in re.findall(rf"\b{re.escape(var)}\.(\w+)\s*\(", clean):
            calls.add((lib, method))
    for lib, method in re.findall(r"getServiceLibrary\(\s*(\w+)\.class\s*\)\s*\.(\w+)\s*\(", clean):
        calls.add((lib, method))
    return sorted(calls)


def method_body(path: Path, name: str) -> tuple[str, int, int] | None:
    source = read_text(path)
    spans = [(s, e) for n, s, e in method_spans(source) if n == name]
    return (source, spans[0][0], spans[0][1]) if spans else None
