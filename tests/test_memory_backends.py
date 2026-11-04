import json
from pathlib import Path

from academic_workspace.companion_contracts import EvidenceRecord
from academic_workspace.memory import JsonlMemoryStore, SqliteMemoryStore
from academic_workspace.companion_kernel import record_evidence


def test_memory_backends_store_the_same_evidence_contract(tmp_path: Path):
    evidence = EvidenceRecord("SINF", "SIG", 2, 1, "Caso", "Duda", ("source/SIG.md",))
    jsonl = JsonlMemoryStore(tmp_path / "evidence.jsonl")
    sqlite = SqliteMemoryStore(tmp_path / "evidence.sqlite3")

    first = record_evidence(tmp_path, evidence, store=jsonl)
    second = record_evidence(tmp_path, evidence, store=sqlite)

    assert first == second
    assert len(jsonl.events()) == 1
    assert len(sqlite.events()) == 1
    assert jsonl.events()[0]["schema"] == "evidence-record.v1"
    assert sqlite.events()[0]["schema"] == "evidence-record.v1"
