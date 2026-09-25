from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / ".github" / "skills" / "recolectar-contrato-apx" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import callgraph  # noqa: E402
import validate  # noqa: E402


EVIDENCE = ROOT / "Json generados" / "experimento" / "B-agente-v3" / "_evidencia" / "ABKOT004-01-AR.txt"


class EvidenceGraph:
    def __init__(self, emissions, methods):
        self.emissions = emissions
        self.methods = methods

    def first_emission_order(self):
        order = []
        for emission in self.emissions:
            if emission.kind != "severity" and not emission.code.startswith("?") and emission.code not in order:
                order.append(emission.code)
        return order


def _build_graph_from_evidence(_root, _concrete):
    text = EVIDENCE.read_text(encoding="utf-8")
    emissions = []
    methods = []

    for path_text in re.findall(r"\[(C:\\[^\]:]+?\.java):\d+\]", text):
        path = Path(path_text)
        if (path, "evidence", 0, 0) not in methods:
            methods.append((path, "evidence", 0, 0))

    code = None
    description = ""
    for line in text.splitlines():
        line = line.rstrip()
        match = re.match(r"\d+\.\s+([A-Z0-9]{12})\s+primera emisión", line.strip())
        if match:
            if code:
                emissions.append(callgraph.Emission("advice", code, "", "evidence", "evidence", description))
            code = match.group(1)
            description = ""
            continue
        if code and "descripción candidata:" in line:
            desc_match = re.search(r"descripción candidata:\s*'(.+)'", line)
            if desc_match:
                description = desc_match.group(1)
                continue
        severity = re.search(r"Severidades:\s+(\w+)", line)
        if severity:
            emissions.append(callgraph.Emission("severity", severity.group(1), "", "evidence", "evidence"))

    if code:
        emissions.append(callgraph.Emission("advice", code, "", "evidence", "evidence", description))

    return EvidenceGraph(emissions, methods)


validate.build_graph = _build_graph_from_evidence

sys.argv = [
    "validate.py",
    str(ROOT / "ud-pricing-rules"),
    str(ROOT / "Json generados" / "experimento" / "B-agente-v3" / "ABKOT004-01-AR.json"),
]

raise SystemExit(validate.main())