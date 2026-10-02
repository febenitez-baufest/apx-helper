"""Genera el expediente de evidencia de una librería APX Tipo B (solo lectura).

Uso: python evidence_lib.py <raiz_proyecto> [--out expediente.txt]

Imprime, con ruta y número de línea, para la librería completa y luego para cada método
`execute*` de su interfaz:
  0. Identidad: POM de interfaz/implementación, apx.json y *-arc.xml completos.
  1. Firma y Javadoc completos de la interfaz (una vez).
  2. Para cada método: cuerpo completo de la implementación.
  3. Librerías APX invocadas (getServiceLibrary) alcanzables desde ese método.
  4. Grafo de llamadas estático desde ese método (→ método, ⚑ emisión, ◆ severidad).
  5. Cuerpo de cada método auxiliar alcanzado (fuera de la clase Impl, ya impresa en el punto 2).
  6. Secuencia DFS de primera emisión de códigos de error (orden obligatorio).
  7. multilanguage-ES.properties si no está vacío; si está vacío, Javadoc de las constantes citadas.
  8. Campos de cada DTO de parámetro, si su fuente está disponible en el proyecto.
Es un índice para leer el código: confirma siempre condiciones, propagación y catch.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_common import (  # noqa: E402
    dto_fields,
    find_library,
    format_type,
    generic_arg,
    java_index,
    javadoc_before,
    library_calls_in_text,
    list_interface_methods,
    method_spans,
    numbered,
    read_text,
)
from callgraph_lib import build_graph_for_method  # noqa: E402


def header(title: str) -> None:
    print(f"\n{'=' * 100}\n## {title}\n{'=' * 100}")


def main() -> int:
    args = sys.argv[1:]
    if "--out" in args:
        position = args.index("--out")
        out = Path(args[position + 1])
        del args[position:position + 2]
        out.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = out.open("w", encoding="utf-8")
    if len(args) != 1:
        print(__doc__)
        return 2
    root = Path(args[0]).resolve()
    library = find_library(root)

    header(f"0. Identidad de {library.library_id}")
    for label, path in (
        ("apx.json", root / "apx.json"),
        ("POM interfaz", library.pom_interface),
        ("POM implementación", library.pom_impl),
        ("POM raíz", library.pom_parent),
    ):
        if path.exists():
            print(f"--- {label}: {path}\n{read_text(path).strip()}")
    for arc in library.arc_xmls:
        print(f"\n--- {arc}\n{read_text(arc).strip()}")

    header("1. Interfaz pública (firma + Javadoc de cada método)")
    print(f"{library.interface_java}\n{read_text(library.interface_java)}")

    methods = list_interface_methods(library.interface_java)
    if not methods:
        print("Sin métodos públicos detectados en la interfaz.")
        return 1

    impl_source = read_text(library.impl_java)
    cited_codes: set[str] = set()

    for method in methods:
        header(f"MÉTODO {method.name}")

        header(f"2. {method.name} - cuerpo completo en {library.impl_java.name}")
        spans = [(s, e) for n, s, e in method_spans(impl_source) if n == method.name]
        if not spans:
            print(f"No se encontró implementación de {method.name} en {library.impl_java}")
            continue
        start, end = spans[0]
        print(numbered(impl_source, start, end))

        header("3. Librerías APX invocadas (getServiceLibrary + llamada) alcanzables desde este método")
        graph = build_graph_for_method(root, library.impl_java, method.name)
        body = impl_source[start:end]
        libs = set(library_calls_in_text(body))
        for path, _, s, e in graph.methods:
            if path != library.impl_java:
                libs |= set(library_calls_in_text(read_text(path)[s:e]))
        for lib, call in sorted(libs):
            print(f"  {lib}.{call}")
        if not libs:
            print("  (ninguna)")

        header("4. Grafo de llamadas estático desde el método (→ método, ⚑ emisión, ◆ severidad)")
        print("\n".join(graph.lines) or "(sin llamadas ni emisiones detectadas)")

        header("5. Cuerpo de cada método alcanzado fuera de la implementación")
        for path, name, s, e in graph.methods:
            if path == library.impl_java:
                continue
            text = read_text(path)
            print(f"\n--- {path}:{name}()\n{numbered(text, s, e)}")

        header("6. Secuencia DFS de primera emisión (orden obligatorio de Error Management)")
        for position, code in enumerate(graph.first_emission_order(), 1):
            where = next(e for e in graph.emissions if e.code == code)
            cited_codes.add(code)
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
        print("Severidades (no aplica en el contrato de librería, solo contexto): "
              + (", ".join(f"{e.code} en {e.method}() [{e.location}]" for e in severities) or "ninguna"))

        header("Parámetros del método (nombre, tipo Java, Format Type)")
        for java_type, name in method.params:
            print(f"  IN  {name}: {java_type}  -> Format Type: {format_type(java_type) or '(vacío)'}")
        if method.return_type not in {"void", "Void", ""}:
            print(f"  OUT returnValue: {method.return_type}  -> Format Type: {format_type(method.return_type) or '(vacío)'}")
        else:
            print("  OUT (el método no devuelve valor)")

    header("7. multilanguage-ES.properties y constantes citadas")
    if library.multilanguage and read_text(library.multilanguage).strip():
        print(f"--- {library.multilanguage}\n{read_text(library.multilanguage).strip()}")
    else:
        print("multilanguage-ES.properties vacío o ausente: usa el Javadoc de la constante en Constants.java.")
        for class_name, paths in java_index(root).items():
            if not any(part.lower() == "constants" for part in paths[0].parts):
                continue
            text = read_text(paths[0])
            for match in re.finditer(r"public static final String (\w+)\s*=\s*\"([^\"]*)\"", text):
                code = match.group(2)
                if code in cited_codes:
                    doc = javadoc_before(text, match.start()) or "(sin Javadoc)"
                    print(f"  {code} ({class_name}.{match.group(1)}): {doc}")

    header("8. DTOs de parámetros: campos declarados (si la fuente está en el proyecto)")
    seen_dtos: set[str] = set()

    def describe_dto(simple: str, depth: int = 0) -> None:
        if simple in seen_dtos or depth > 2:
            return
        seen_dtos.add(simple)
        fields = dto_fields(root, simple)
        if not fields:
            print(f"  {'  ' * depth}{simple}: fuente no disponible en el proyecto (DTO de artifact externo)")
            return
        print(f"  {'  ' * depth}{simple}:")
        for field_name, field_type, javadoc in fields:
            print(f"  {'  ' * depth}  - {field_name}: {field_type}  {('(' + javadoc + ')') if javadoc else ''}")
            inner = generic_arg(field_type) or (field_type if format_type(field_type) == "bean" else None)
            if inner and format_type(inner) == "bean":
                describe_dto(inner, depth + 1)

    for method in methods:
        for java_type, _ in method.params:
            simple = java_type.rsplit(".", 1)[-1].rstrip("[]")
            if format_type(java_type) == "bean":
                describe_dto(simple)
            inner = generic_arg(java_type)
            if inner and format_type(inner) == "bean":
                describe_dto(inner)
        if format_type(method.return_type) == "bean":
            describe_dto(method.return_type.rsplit(".", 1)[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
