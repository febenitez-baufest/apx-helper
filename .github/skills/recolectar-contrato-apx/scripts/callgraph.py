"""Grafo de llamadas estático desde execute() y secuencia DFS de emisiones de error.

Es léxico y conservador: sigue llamadas a métodos del proyecto resueltas por tipo
declarado, llamadas estáticas, this/super y librerías obtenidas con getServiceLibrary.
No evalúa condiciones: todas las ramas se consideran alcanzables (regla del prompt).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from apx_common import java_index, line_of, method_spans, read_text, resolve_code, strip_code

CALL = re.compile(r"(?:(\b[A-Za-z_]\w*)\s*\.\s*)?\b([a-z_]\w*)\s*\(|\b([A-Za-z_]\w*)::([a-z_]\w*)")
EMIT = re.compile(r"addAdvice(?:WithDescription)?\s*\(|throw\s+new\s+(\w*Exception)\s*\(|setSeverity\s*\(")
DECL = re.compile(r"\b([A-Z]\w*)(?:<[^;(){}]*?>)?\s+([a-z_]\w*)\s*(?==|;|,|\)|:)")
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "super", "this", "synchronized", "throw"}
CODE = re.compile(r"^[A-Z0-9]{4}\d{8}$")


@dataclass
class Emission:
    kind: str
    code: str
    raw: str
    location: str
    method: str
    description: str = ""
    conditions: str = ""


@dataclass
class Graph:
    lines: list[str] = field(default_factory=list)
    emissions: list[Emission] = field(default_factory=list)
    methods: list[tuple[Path, str, int, int]] = field(default_factory=list)

    def first_emission_order(self) -> list[str]:
        order: list[str] = []
        for emission in self.emissions:
            if emission.kind != "severity" and not emission.code.startswith("?") and emission.code not in order:
                order.append(emission.code)
        return order


class CallGraph:
    def __init__(self, root: Path, library_vars: dict[str, str] | None = None) -> None:
        self.root = root
        self.index = java_index(root)
        self.library_vars = library_vars or {}
        self.graph = Graph()
        self.printed: set[tuple[Path, str]] = set()
        self.walked: set[tuple[Path, str, int]] = set()

    def class_file(self, name: str) -> Path | None:
        impl = [p for p in self.index.get(f"{name}Impl", []) if "dtos" not in p.parts]
        own = [p for p in self.index.get(name, []) if "dtos" not in p.parts]
        return (impl or own or [None])[0]

    def superclass(self, path: Path) -> Path | None:
        match = re.search(r"\bextends\s+(\w+)", strip_code(read_text(path)))
        return self.class_file(match.group(1)) if match else None

    def find_method(self, path: Path | None, name: str) -> tuple[Path, list[tuple[int, int]]] | None:
        seen = set()
        while path and path not in seen:
            seen.add(path)
            spans = [(s, e) for m, s, e in method_spans(read_text(path)) if m == name]
            if spans:
                return path, spans
            path = self.superclass(path)
        return None

    def var_types(self, source: str, start: int, end: int) -> dict[str, str]:
        clean = strip_code(source)
        types = {var: typ for typ, var in DECL.findall(clean)}
        types.update({var: typ for typ, var in DECL.findall(clean[start:end])})
        types.update(self.library_vars)
        return types

    def walk(self, path: Path, name: str, depth: int = 0, stack: tuple = ()) -> None:
        found = self.find_method(path, name)
        indent = "  " * depth
        if not found:
            return
        path, spans = found
        if len(spans) > 1:
            self.graph.lines.append(f"{indent}! {path.stem}.{name}: {len(spans)} sobrecargas; se recorren todas, verifica la firma")
        for start, end in spans:
            key = (path, name, start)
            if key in stack:
                self.graph.lines.append(f"{indent}↻ {path.stem}.{name} (ciclo)")
                continue
            # Un segundo recorrido no puede adelantar ninguna primera emisión.
            if key in self.walked:
                self.graph.lines.append(f"{indent}↺ {path.stem}.{name}() (ya recorrido arriba)")
                continue
            self.walked.add(key)
            source = read_text(path)
            self.graph.lines.append(f"{indent}→ {path.stem}.{name}()  [{path}:{line_of(source, start)}]")
            if (path, name) not in self.printed:
                self.printed.add((path, name))
                self.graph.methods.append((path, name, start, end))
            self.visit_body(path, source, start, end, name, depth, stack + (key,))

    def visit_body(self, path: Path, source: str, start: int, end: int, name: str, depth: int, stack: tuple) -> None:
        clean = strip_code(source)
        body_start = clean.find("{", start) + 1
        types = self.var_types(source, start, end)
        events = []
        for match in EMIT.finditer(clean, body_start, end):
            events.append((match.start(), "emit", match))
        for match in CALL.finditer(clean, body_start, end):
            if match.group(3):
                events.append((match.start(), "call", match))
                continue
            if match.group(2) in KEYWORDS or clean[max(0, match.start() - 4):match.start()].endswith("new "):
                continue
            if re.match(r"addAdvice|setSeverity", match.group(2)):
                continue
            events.append((match.start(), "call", match))
        for _, kind, match in sorted(events, key=lambda e: e[0]):
            if kind == "emit":
                self.record(path, source, match, name, depth)
            else:
                self.follow(path, match, types, depth, stack)

    def follow(self, path: Path, match: re.Match, types: dict[str, str], depth: int, stack: tuple) -> None:
        receiver, method = (match.group(3), match.group(4)) if match.group(3) else (match.group(1), match.group(2))
        if receiver in (None, "this"):
            target = path
        elif receiver == "super":
            target = self.superclass(path)
        elif receiver[0].isupper():
            target = self.class_file(receiver)
        else:
            typ = types.get(receiver)
            target = self.class_file(typ) if typ else None
        if target and self.find_method(target, method):
            self.walk(target, method, depth + 1, stack)

    def record(self, path: Path, source: str, match: re.Match, method: str, depth: int) -> None:
        clean = strip_code(source)
        j = clean.find("(", match.start())
        k, level = j, 0
        while k < len(clean):
            level += {"(": 1, ")": -1}.get(clean[k], 0)
            if level == 0:
                break
            k += 1
        raw = re.sub(r"\s+", " ", source[match.start():k + 1])
        args = split_args(source[j + 1:k]) if source[j + 1:k].strip() else [""]
        location = f"{path}:{line_of(source, match.start())}"
        indent = "  " * (depth + 1)
        if raw.startswith("setSeverity"):
            enum = re.search(r"Severity\.(\w+)", raw)
            value = enum.group(1) if enum else "?"
            self.graph.emissions.append(Emission("severity", value, raw, location, method))
            self.graph.lines.append(f"{indent}◆ SEVERITY {value}  [{location}]")
            return
        kind = "throw" if raw.startswith("throw") else "advice"
        code = resolve_code(args[0], self.root, path) if args[0] else "?"
        if not CODE.match(code):
            code = f"?{args[0] or code}"
        label = "EMITE" if not code.startswith("?") else "PROPAGA/NO RESUELTO"
        description = expected_description(args[1], self.root, path) if len(args) > 1 else ""
        if not description and kind == "advice":
            previous = source[:match.start()].splitlines()[-3:]
            log = next((m for line in reversed(previous) for m in [re.search(r'LOGGER\.(?:error|warn)\(\s*"([^"{}]+)"\s*\)', line)] if m), None)
            if log:
                description = f"[log adyacente candidato] {log.group(1)}"
        conditions = enclosing_conditions(source, clean, match.start())
        self.graph.emissions.append(Emission(kind, code, raw, location, method, description, conditions))
        self.graph.lines.append(f"{indent}⚑ {label} {kind} código={code}  [{location}]  {raw[:240]}")
        if conditions:
            self.graph.lines.append(f"{indent}  bajo: {conditions}")
        if description:
            self.graph.lines.append(f"{indent}  descripción esperada: {description!r}")


def expected_description(expression: str, root: Path, owner: Path | None = None) -> str:
    """Texto canónico de una descripción: literal, constante, String.format o concatenación con {expr}."""
    expression = expression.strip()
    fmt = re.fullmatch(r"String\.format\s*\((.*)\)", expression, re.S)
    if fmt:
        return expected_description(split_args(fmt.group(1))[0], root, owner)
    parts = split_concat(expression)
    text = ""
    for part in parts:
        literal = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', part)
        resolved = resolve_code(part, root, owner) if re.fullmatch(r"(?:\w+\.)*[A-Z][A-Z0-9_]+", part) else "?"
        if literal:
            text += literal.group(1)
        elif not resolved.startswith("?"):
            text += resolved
        elif len(parts) == 1:
            return ""
        else:
            text += "{" + re.sub(r"\s+", " ", part) + "}"
    return re.sub(r"\s+", " ", text).strip()


def split_concat(expression: str) -> list[str]:
    parts, depth, current, quote = [], 0, "", False
    for index, char in enumerate(expression):
        if char == '"' and (index == 0 or expression[index - 1] != "\\"):
            quote = not quote
        if not quote:
            depth += {"(": 1, ")": -1}.get(char, 0)
            if char == "+" and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
        current += char
    parts.append(current.strip())
    return [p for p in parts if p]


def enclosing_conditions(source: str, clean: str, position: int) -> str:
    """Cabeceras de control (if/else/catch/for/while/case) que envuelven una posición dentro de su método."""
    owner = next(((s, e) for _, s, e in method_spans(source) if s <= position < e), None)
    if owner is None:
        return ""
    stack: list[tuple[int, int]] = []
    last = clean.find("{", owner[0]) + 1
    for index in range(last, position):
        char = clean[index]
        if char == "{":
            stack.append((last, index))
            last = index + 1
        elif char == "}":
            if stack:
                stack.pop()
            last = index + 1
        elif char == ";":
            last = index + 1
    headers = []
    for start, end in stack:
        text = re.sub(r"\s+", " ", source[start:end]).strip()
        text = re.sub(r"^\}\s*", "", text)
        if re.match(r"(?:\}\s*)?(?:if|else|catch|for|while|case|switch|try)\b", text):
            headers.append(text[:160])
    return " › ".join(headers)


def split_args(args: str) -> list[str]:
    parts, depth, current, quote = [], 0, "", False
    for index, char in enumerate(args):
        if char == '"' and (index == 0 or args[index - 1] != "\\"):
            quote = not quote
        if not quote:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            if char == "," and depth == 0:
                parts.append(current)
                current = ""
                continue
        current += char
    parts.append(current)
    return [p.strip() for p in parts]


def build_graph(root: Path, concrete: Path) -> Graph:
    clean = strip_code(read_text(concrete))
    library_vars = {var: lib for var, lib in re.findall(r"(\w+)\s*=\s*(?:this\.)?getServiceLibrary\(\s*(\w+)\.class\s*\)", clean)}
    graph = CallGraph(root, library_vars)
    graph.walk(concrete, "execute")
    return graph.graph
