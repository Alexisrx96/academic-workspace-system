from pathlib import Path

from academic_workspace.assessment import build_diagnostic_comparison


def test_diagnostic_comparison_is_generated_from_student_registry(tmp_path: Path):
    registry = tmp_path / "Proyectos de Estudio" / "SINF - Parcial 1" / "Registro de diagnósticos.md"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "# Registro de diagnósticos\n\n"
        "| Fecha | Intento | Bloque | Explicación | Aplicación | Evidencia de aplicación | Duda |\n"
        "|---|---|---|---:|---:|---|---|\n"
        "| 2026-08-18 | Inicial | SIG | 1/3 | 0/3 | — | Confundo conceptos |\n"
        "| 2026-08-20 | Segundo | SIG | 2/3 | 2/3 | Modelo de ventas | — |\n",
        encoding="utf-8",
    )

    report = build_diagnostic_comparison(tmp_path)

    assert "SINF" in report
    assert "1/3" in report
    assert "2/3" in report
    assert "Modelo de ventas" in report
    assert "aplicado" in report
