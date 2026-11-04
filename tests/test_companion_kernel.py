import json
from pathlib import Path

from academic_workspace.companion_kernel import build_context, record_evidence, start_session
from academic_workspace.companion_contracts import EvidenceRecord


def test_companion_context_and_start_session_are_harness_independent(tmp_path: Path):
    control = tmp_path / "Control Académico"
    control.mkdir(parents=True)
    (control / "00 - Dashboard académico.md").write_text(
        "# Dashboard\n\n## Atención ahora\n\n- [ ] **Prioridad** · [SIG](../Blackboard/SINF/SIG.md) — SINF\n\n## Vistas de control\n",
        encoding="utf-8",
    )
    (control / "Matriz de dominio.md").write_text(
        "| Curso | Bloque | Explicación | Aplicación | Duda o error | Próxima acción | Próximo repaso | Fuente |\n"
        "|---|---|---:|---:|---|---|---|---|\n"
        "| SINF | SIG | — | — | — | — | — | — |\n"
        "| SINF | Datos | — | — | — | — | — | — |\n",
        encoding="utf-8",
    )
    context = build_context(tmp_path)
    action = start_session(tmp_path)

    assert context.to_dict()["schema"] == "study-context.v1"
    assert action.to_dict()["action"] == "start_session"
    assert action.course == "SINF"
    assert action.topic == "SIG"
    phases = [step["phase"] for step in action.parameters["plan"]]
    assert phases == ["retrieval", "focused", "interleaving", "application", "adversarial"]
    assert sum(step["minutes"] for step in action.parameters["plan"]) == 25


def test_record_evidence_is_idempotent(tmp_path: Path):
    evidence = EvidenceRecord("SINF", "SIG", 2, 1, "Caso", "Duda", ("Blackboard/SINF/SIG.md",))

    first = record_evidence(tmp_path, evidence)
    second = record_evidence(tmp_path, evidence)
    lines = (tmp_path / ".blackboard-sync" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()

    assert first == second
    assert len(lines) == 1
    assert json.loads(lines[0])["event_id"] == first
