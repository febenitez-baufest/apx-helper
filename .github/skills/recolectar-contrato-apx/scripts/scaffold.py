"""Genera el esqueleto determinista del contrato de una transacción APX.

Uso: python scaffold.py <raiz_proyecto> <ID_TRANSACCION> <salida.json> [--force]

Rellena desde el XML/POM/código: descripción funcional, Country, Version, Transaction
Identifier, librerías invocadas y el inventario completo y ordenado de parámetros.
Todo lo que requiere análisis queda como "__TODO__:<ruta>" único y editable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apx_common import TODO, Module, canonical_rows, functional_description, library_calls, xml_root, xml_section  # noqa: E402


def build(root: Path, tx_id: str) -> dict:
    module = Module(root, tx_id)
    if not module.xml.exists() or len(module.concrete) != 1:
        raise SystemExit(f"{tx_id}: módulo no procesable (XML={module.xml.exists()}, concretas={len(module.concrete)})")
    xml = xml_root(module)

    def rows(section: str, label: str) -> list[dict]:
        return [
            {
                "Name of APX field": row["Name of APX field"],
                "Mandatory?": row["Mandatory?"],
                "APX data type": row["APX data type"],
                "Description": f"{TODO}:{label}:{row['Name of APX field']}",
            }
            for row in canonical_rows(xml_section(xml, section))
        ]

    return {
        "TRANSACTION - FUNCTIONAL DESCRIPTION": functional_description(module),
        "EXECUTION FLOWS - DETAILED DESCRIPTION": f"{TODO}:EXECUTION FLOWS",
        "TECHNICAL DATA": {
            "Country": xml.get("country") or tx_id.rsplit("-", 1)[-1],
            "Version": xml.get("version") or tx_id.split("-")[1],
            "Migration - Origin from Host": f"{TODO}:Migration",
            "Asynchronous?": f"{TODO}:Asynchronous?",
            "Transactional?": f"{TODO}:Transactional?",
            "Asynchronous Consumers": f"{TODO}:Asynchronous Consumers (array)",
            "Transaction Identifier": xml.get("transactionName") or tx_id.split("-")[0],
            "Accessed Libraries": [
                {"Library Identifier": lib, "Method": method, "Description": f"{TODO}:Library:{lib}.{method}"}
                for lib, method in library_calls(module.concrete[0])
            ],
            "Error Management": f"{TODO}:Error Management (array)",
            "Events to which it is subscribed": f"{TODO}:Events (array)",
        },
        "PARAMETERS": {
            "Input Parameters": rows("paramsIn", "IN"),
            "Output Parameters": rows("paramsOut", "OUT"),
        },
    }


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--force"]
    if len(args) != 3:
        print(__doc__)
        return 2
    root, tx_id, out = Path(args[0]).resolve(), args[1], Path(args[2])
    if out.exists() and "--force" not in sys.argv:
        print(f"{out} ya existe; usa --force para regenerarlo desde cero", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(root, tx_id), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Esqueleto escrito en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
