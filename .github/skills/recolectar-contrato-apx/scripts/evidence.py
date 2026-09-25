"""Genera el expediente de evidencia de una transacción APX (solo lectura).

Uso: python evidence.py <raiz_proyecto> <ID_TRANSACCION> [--out expediente.txt]

Imprime, con ruta y número de línea:
  1. la clase concreta completa y los setters de salida (addParameter) de la abstracta;
  2. firma y Javadoc de cada método de librería invocado;
  3. el grafo de llamadas estático desde execute() con las emisiones en orden DFS;
  4. el cuerpo de cada método alcanzado;
  5. la secuencia DFS de primera emisión de códigos y las severidades encontradas;
  6. properties relacionados y marcadores explícitos de transaccionalidad/asincronía.
Es un índice para leer el código: confirma siempre condiciones, propagación y catch.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apx_common import (  # noqa: E402
    Module,
    canonical_rows,
    explicit_markers,
    java_index,
    library_calls,
    library_files,
    line_of,
    method_spans,
    numbered,
    read_text,
    strip_code,
    xml_root,
    xml_section,
)
from callgraph import build_graph  # noqa: E402


def header(title: str) -> None:
    print(f"\n{'=' * 100}\n## {title}\n{'=' * 100}")


def javadoc_before(source: str, index: int) -> str:
    before = source[:index].rstrip()
    if before.endswith("*/"):
        start = before.rfind("/**")
        if start >= 0:
            return re.sub(r"\s*\n\s*\*\s?", " ", before[start + 3:-2]).strip()
    return ""


def main() -> int:
    args = sys.argv[1:]
    if "--out" in args:
        position = args.index("--out")
        out = Path(args[position + 1])
        del args[position:position + 2]
        out.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = out.open("w", encoding="utf-8")
    if len(args) != 2:
        print(__doc__)
        return 2
    root, tx_id = Path(args[0]).resolve(), args[1]
    module = Module(root, tx_id)
    if len(module.concrete) != 1:
        print(f"{tx_id}: clases concretas encontradas = {module.concrete}; módulo ambiguo o no procesable")
        return 1
    concrete = module.concrete[0]

    header(f"1. {tx_id} - clase concreta completa")
    source = read_text(concrete)
    print(f"{concrete}\n{numbered(source, 0, len(source))}")

    header("1b. Clase abstracta - métodos con addParameter (salidas): ¿hay guarda antes de addParameter?")
    for abstract in module.abstract:
        text = read_text(abstract)
        for _, start, end in method_spans(text):
            if "addParameter" in text[start:end]:
                print(f"\n{abstract}:{line_of(text, start)}\n{numbered(text, start, end)}")

    header("2. Librerías invocadas (getServiceLibrary + llamada)")
    for library, method in library_calls(concrete):
        interface, impl = library_files(root, library)
        print(f"\n{library}.{method}  interfaz={interface}  impl={impl}")
        if interface:
            text = read_text(interface)
            match = re.search(rf"[^;\n]*\b{method}\s*\([^;]*\);", text)
            if match:
                print(f"  Firma ({interface.name}:{line_of(text, match.start())}): {' '.join(match.group(0).split())}")
                print(f"  Javadoc: {javadoc_before(text, match.start()) or '(sin Javadoc)'}")

    graph = build_graph(root, concrete)
    header("3. Grafo de llamadas estático desde execute() (→ método, ⚑ emisión, ◆ severidad)")
    print("\n".join(graph.lines))

    header("4. Cuerpo de cada método alcanzado (excepto la clase concreta, ya impresa)")
    for path, name, start, end in graph.methods:
        if path == concrete:
            continue
        text = read_text(path)
        print(f"\n--- {path}:{line_of(text, start)} {name}()\n{numbered(text, start, end)}")

    header("5. Secuencia DFS de primera emisión (orden requerido para Error Management)")
    for position, code in enumerate(graph.first_emission_order(), 1):
        where = next(e for e in graph.emissions if e.code == code)
        print(f"{position}. {code}  primera emisión {where.kind} en {where.method}()  [{where.location}]")
        for emission in [e for e in graph.emissions if e.code == code]:
            print(f"     disparo en {emission.method}(): {emission.conditions or '(sin condición envolvente en el método)'}")
        descriptions = sorted({e.description for e in graph.emissions if e.code == code and e.description})
        for description in descriptions:
            print(f"     descripción candidata: {description!r}")
    unresolved = [e for e in graph.emissions if e.kind != "severity" and e.code.startswith("?")]
    for emission in unresolved:
        print(f"   · no resuelto ({emission.code}) en {emission.method}() [{emission.location}]: {emission.raw[:160]}")
    severities = [e for e in graph.emissions if e.kind == "severity"]
    print("Severidades: " + (", ".join(f"{e.code} en {e.method}() [{e.location}]" for e in severities) or "ninguna"))

    header("6. multilanguage-ES.properties y marcadores explícitos")
    files = sorted({p for p, *_ in graph.methods})
    module_dirs = {f.parents[f.parts[::-1].index("src")] for f in files if "src" in f.parts} | {module.dir}
    for props in sorted({p for d in module_dirs for p in d.rglob("multilanguage-ES.properties") if "target" not in p.parts}):
        print(f"--- {props}\n{read_text(props).strip() or '(vacío)'}")
    markers = explicit_markers(root, module, files)
    for kind, hits in markers.items():
        print(f"{kind}: {len(hits)} coincidencias")
        for hit in hits:
            print(f"  {hit}")
    if not any(markers.values()):
        print("Sin evidencia explícita: Asynchronous? y Transactional? = marcador; Asynchronous Consumers y Events = []")

    header("7. Accesos por campo en métodos alcanzables (get<Campo>/set<Campo>/builder)")
    print("Salida sin acceso detectado => antes de afirmar que se devuelve un valor, busca constructor, copia o mapper; si no existe, es null/vacío salvo que el DTO de entrada se devuelva tal cual.")
    print("Un default aplicado solo al construir parámetros SQL (Map.of/put para INSERT/UPDATE) NO es el valor devuelto en el DTO.")
    xml = xml_root(module)
    bodies = [(p, n, read_text(p)[s:e], line_of(read_text(p), s)) for p, n, s, e in graph.methods]
    for section in ("paramsIn", "paramsOut"):
        print(f"\n[{section}]")
        rows = canonical_rows(xml_section(xml, section))
        packages = {r["Name of APX field"]: r["_package"].rsplit(".", 1)[-1] for r in rows if r["_package"]}
        for row in rows:
            leaf = row["Name of APX field"].split(".")[-1]
            parent = row["Name of APX field"].rsplit(".", 1)[0] if "." in row["Name of APX field"] else ""
            capital = leaf[:1].upper() + leaf[1:]
            pattern = re.compile(rf"\.(get|set|is){re.escape(capital)}\s*\(|\b{re.escape(leaf)}\s*\(")
            ctor = re.compile(rf"new\s+{re.escape(packages[parent])}\s*\(\s*[^)\s]") if packages.get(parent) else None
            hits = []
            for path, name, body, first in bodies:
                for number, line in enumerate(body.splitlines(), first):
                    clean_line = strip_code(line)
                    found = pattern.search(clean_line)
                    if found:
                        hits.append(f"{found.group(1) or 'call'}@{path.stem}.{name}:{number}")
                    elif ctor and ctor.search(clean_line):
                        hits.append(f"ctor({packages[parent]})@{path.stem}.{name}:{number}")
            summary = ", ".join(hits[:8]) + (" …" if len(hits) > 8 else "")
            print(f"  {row['Name of APX field']}: {summary or 'sin acceso detectado (revisa constructores, copias o mappers antes de concluir)'}")

    header("8. DTOs de parámetros: accesores NO triviales e inicializadores de campo")
    print("Un getter/setter con lógica (default, conversión, generación) transforma el valor: NUNCA lo describas como 'without transformation'.")
    print("Un campo sin inicializador y sin set alcanzable queda null (no 'empty').")
    index = java_index(root)
    trivial = re.compile(r"^\{\s*(?:return\s+(?:this\.)?\w+\s*;|(?:this\.)?\w+\s*=\s*\w+\s*;)?\s*\}$")
    seen_classes = set()
    for section in ("paramsIn", "paramsOut"):
        for row in canonical_rows(xml_section(xml, section)):
            simple = row["_package"].rsplit(".", 1)[-1] if row["_package"] else ""
            if not simple or simple in seen_classes:
                continue
            seen_classes.add(simple)
            for path in index.get(simple, []):
                text = read_text(path)
                clean = strip_code(text)
                print(f"\n--- {simple} ({row['Name of APX field']}) {path}")
                for field_match in re.finditer(r"(?m)^\s*private\s+(?!static)[\w<>\[\], ]+\s+(\w+)\s*=\s*([^;]+);", clean):
                    print(f"  inicializador {line_of(text, field_match.start())}: {field_match.group(1)} = {text[field_match.start(2):field_match.end(2)].strip()}")
                for name, start, end in method_spans(text):
                    if not re.match(r"(get|set|is)[A-Z]", name):
                        continue
                    body = re.sub(r"\s+", " ", clean[clean.find("{", start):end])
                    if not trivial.match(body):
                        print(numbered(text, start, end))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
