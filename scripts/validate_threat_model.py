"""Validate schema, exact T01–T20 inventory, DFD scope and STRIDE parity."""
import json
import re
from pathlib import Path
import jsonschema


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(root):
    folder = root / "docs/diagramas/threat-model"
    model = json.loads((folder / "threat-dragon-model.json").read_text(encoding="utf-8"))
    schema = json.loads((folder / "threat-dragon-v2.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(model, schema)
    diagrams = model["detail"]["diagrams"]
    require(len(diagrams) == 2 and {d["id"] for d in diagrams} == {0, 1}, "Expected DFD 0 and 1")
    require(model["detail"]["threatTop"] == 20, "threatTop must be 20")
    inventory = {}
    threat_ids = set()
    for diagram in diagrams:
        cells = diagram["cells"]
        ids = [c["id"] for c in cells]
        require(len(ids) == len(set(ids)), "Duplicate cell ID")
        require(any(c["data"].get("isTrustBoundary") for c in cells), "Missing trust boundary")
        for cell in cells:
            if cell["shape"] == "flow":
                require(cell["source"]["cell"] in ids and cell["target"]["cell"] in ids,
                        "Dangling flow: " + cell["id"])
            threats = cell.get("data", {}).get("threats", [])
            require(bool(cell["data"].get("hasOpenThreats")) == bool(threats),
                    "Incorrect hasOpenThreats: " + cell["id"])
            for threat in threats:
                n = threat["number"]
                expected_status = "Mitigated" if n in {13, 15} else "Open"
                require(
                    threat["status"] == expected_status,
                    f"Unexpected status T{n:02}: expected {expected_status}, got {threat['status']}"
                )
                require(n not in inventory, f"Duplicate T{n:02}")
                require(threat["threatId"] not in threat_ids, "Duplicate threatId")
                require(threat["threatId"] == f"iam-threat-{n}", "Changed threat identity")
                require(threat["title"].startswith(f"T{n:02} "), "Title/number mismatch")
                inventory[n] = (cell["id"], threat)
                threat_ids.add(threat["threatId"])
    require(set(inventory) == set(range(1, 21)), "Expected exactly T01–T20, without gaps or duplicates")
    level1 = {c["id"]: c for d in diagrams if d["id"] == 1 for c in d["cells"]}
    for name, shape in {"spa": "process", "grid": "process", "permissions": "process",
                        "idp": "process", "db": "store", "grants": "store", "loads": "store",
                        "browser-panel": "trust-boundary-box", "browser-grid": "trust-boundary-box"}.items():
        require(name in level1 and level1[name]["shape"] == shape, "Missing component: " + name)
    expected = {
        "f26": ("spa", "grid", "postMessage"), "f27": ("grid", "spa", "postMessage"),
        "f28": ("grid", "permissions", "HTTP"), "f29": ("permissions", "grid", "HTTP"),
        "f30": ("spa", "permissions", "HTTP"), "f31": ("permissions", "spa", "HTTP"),
        "f32": ("permissions", "idp", "HTTP"), "f33": ("idp", "permissions", "HTTP"),
        "f34": ("permissions", "db", "PostgreSQL"), "f35": ("db", "permissions", "PostgreSQL"),
        "f36": ("permissions", "grants", "PostgreSQL"), "f37": ("grants", "permissions", "PostgreSQL"),
        "f38": ("permissions", "outbox", "PostgreSQL"),
        "f39": ("spa", "idp", "HTTP"), "f40": ("idp", "spa", "HTTP"),
        "f41": ("idp", "loads", "PostgreSQL"), "f42": ("loads", "idp", "PostgreSQL"),
        "f43": ("idp", "grants", "PostgreSQL"),
    }
    for fid, endpoints in expected.items():
        require(fid in level1, "Missing flow: " + fid)
        c = level1[fid]
        require(c["shape"] == "flow" and
                (c["source"]["cell"], c["target"]["cell"], c["data"]["protocol"]) == endpoints,
                "Incorrect flow/protocol: " + fid)
    matrix = (root / "docs/seguridad/stride-matrix.md").read_text(encoding="utf-8")
    rows = [line for line in matrix.splitlines() if re.match(r"^\| T\d+ \|", line)]
    require(len(rows) == 20, "STRIDE must contain 20 rows")
    seen = set()
    categories = {"Spoofing": "S", "Tampering": "T", "Repudiation": "R",
                  "Information disclosure": "I", "Denial of service": "D", "Elevation of privilege": "E"}
    for row in rows:
        fields = [field.strip() for field in row.strip("|").split("|")]
        n = int(fields[0][1:])
        require(n in inventory and n not in seen, "Invalid/duplicate matrix ID")
        element, threat = inventory[n]
        require(fields == [f"T{n:02}", categories[threat["type"]], element,
                           threat["title"][4:], threat["severity"], threat["mitigation"]],
                f"JSON/STRIDE mismatch: T{n:02}")
        seen.add(n)
    print("Schema and references OK: 2 diagrams, 18 open threats, 2 mitigated threats")
    print("Scope and STRIDE parity OK: T01–T20, components and 18 new flows")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
