from __future__ import annotations

from typing import Any


def build_study_answer(course_answer: str, external_support: str, conflicts_or_simplifications: str, technical_conclusion: str, source_refs: tuple[str, ...]) -> dict[str, Any]:
    return {
        "schema": "study-answer.v1",
        "course_answer": course_answer,
        "external_support": external_support,
        "conflicts_or_simplifications": conflicts_or_simplifications,
        "technical_conclusion": technical_conclusion,
        "source_refs": list(source_refs),
    }
