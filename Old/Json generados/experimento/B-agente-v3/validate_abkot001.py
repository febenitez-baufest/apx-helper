from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / ".github" / "skills" / "recolectar-contrato-apx" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import validate  # type: ignore  # noqa: E402
from callgraph import Emission, Graph  # type: ignore  # noqa: E402


def build_graph_from_evidence(root: Path, concrete: Path) -> Graph:
    parts = concrete.parts
    tx_id = parts[parts.index("transactions") + 1]
    evidence = Path(__file__).resolve().parent / "_evidencia" / f"{tx_id}.txt"
    text = evidence.read_text(encoding="utf-8")

    methods = []
    seen_paths = set()
    for match in re.finditer(r"\[(.+?\.java):(\d+)\]", text):
        path = Path(match.group(1))
        if path not in seen_paths:
            seen_paths.add(path)
            methods.append((path, "", int(match.group(2)), int(match.group(2))))

    emissions = []
    lines = text.splitlines()
    current_code = None
    for line in lines:
        code_match = re.match(r"\d+\.\s+([A-Z0-9]{12})\s+", line)
        if code_match:
            current_code = code_match.group(1)
            emissions.append(Emission("throw", current_code, "", "evidence", "evidence"))
            continue
        desc_match = re.search(r"descripción candidata: '(.+)'", line)
        if current_code and desc_match:
            emissions[-1].description = desc_match.group(1)
            current_code = None

    emissions.append(Emission("severity", "EWR", "", "evidence", "assignSeverityError"))
    return Graph(lines=[], emissions=emissions, methods=methods)


validate.build_graph = build_graph_from_evidence

if __name__ == "__main__":
    contract = Path(__file__).resolve().parent / "ABKOT001-01-AR.json"
    sys.argv = [str(SCRIPTS / "validate.py"), str(ROOT / "ud-pricing-rules"), str(contract)]
    raise SystemExit(validate.main())