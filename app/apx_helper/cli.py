"""Interfaz de línea de comandos de apx-helper."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .contracts import TRANSACTION, ContractError, load_contracts
from .generator import render


def _cmd_render(args: argparse.Namespace) -> int:
    transactions: list[dict] = []
    transaction_sources: list[str] = []
    single_jobs: list[tuple[str, dict]] = []

    for source in args.contract:
        try:
            loaded = load_contracts(source)
        except (ContractError, FileNotFoundError) as exc:
            print(f"[ERROR] {source}: {exc}", file=sys.stderr)
            return 1
        for data, kind in loaded:
            if kind == TRANSACTION and not args.split:
                transactions.append(data)
                if str(source) not in transaction_sources:
                    transaction_sources.append(str(source))
            else:
                single_jobs.append((str(source), data))

    results: list[tuple[str, object]] = []
    try:
        if transactions:
            results.append((", ".join(transaction_sources), render(transactions, name=args.name)))
        for source, data in single_jobs:
            results.append((source, render(data, library_id=args.library_id, name=args.name)))
    except (ContractError, FileNotFoundError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    total_issues = 0
    for source, result in results:
        destination = result.save(args.output)
        print(f"[OK] {source} -> {destination}")
        for issue in result.issues:
            total_issues += 1
            print(f"  [{issue.severity.upper()}] {issue}")

    if total_issues:
        print(f"\n{total_issues} pendiente(s) resaltados en ámbar para revisión manual.")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    failed = False
    for source in args.contract:
        try:
            loaded = load_contracts(source)
        except (ContractError, FileNotFoundError) as exc:
            failed = True
            print(f"[ERROR] {source}: {exc}", file=sys.stderr)
        else:
            kinds = ", ".join(kind for _, kind in loaded)
            print(f"[OK] {source}: {len(loaded)} contrato(s) válido(s) ({kinds}).")
    return 1 if failed else 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Instala las dependencias de API: pip install fastapi uvicorn", file=sys.stderr)
        return 1
    print(f"Interfaz disponible en http://{args.host}:{args.port}/")
    uvicorn.run("apx_helper.api:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apx-helper",
        description="Rellena las plantillas APX Global Sheet a partir de contratos JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser(
        "render",
        help="Genera el Excel de uno o varios contratos.",
        description=(
            "Varias transacciones se combinan en un mismo libro (una hoja por transacción); "
            "cada librería genera su propio libro."
        ),
    )
    render_parser.add_argument("contract", nargs="+", type=Path, help="Contrato(s) JSON de entrada.")
    render_parser.add_argument(
        "-o", "--output", type=Path, default=Path("salida"), help="Carpeta de salida (por defecto: ./salida)."
    )
    render_parser.add_argument(
        "--library-id", help="Identificador de la librería (p. ej. ADVSR500); solo contratos de librería."
    )
    render_parser.add_argument("--name", help="Sobrescribe el nombre base del archivo generado.")
    render_parser.add_argument(
        "--split", action="store_true", help="Genera un archivo por transacción en lugar de combinarlas."
    )
    render_parser.set_defaults(func=_cmd_render)

    validate_parser = subparsers.add_parser("validate", help="Valida contratos sin generar Excel.")
    validate_parser.add_argument("contract", nargs="+", type=Path)
    validate_parser.set_defaults(func=_cmd_validate)

    serve_parser = subparsers.add_parser("serve", help="Arranca la API REST y la interfaz web.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true")
    serve_parser.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
