from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

from .source_config import load_source_configs


CHECKPOINT_DIR = "Checkpoint - Parcial 1"
STUDY_PROJECTS_DIR = "Proyectos de Estudio"


@dataclass(frozen=True)
class Topic:
    title: str
    objective: str
    retrieve: str
    apply: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class CourseSpec:
    code: str
    name: str
    exam_evidence: str
    topics: tuple[Topic, ...]


@dataclass(frozen=True)
class CheckpointResult:
    root: Path
    course_count: int
    panel_path: Path


SPECS: dict[str, CourseSpec] = {
    "LEMA": CourseSpec(
        code="LEMA",
        name="Lenguaje de Máquina",
        exam_evidence="E1_P1 Examen Parcial Ordinario y E1_A1 de la semana 4.",
        topics=(
            Topic("Entorno de ejecución y ensamblador", "Explicar qué necesita un programa ensamblador para ejecutarse y el papel de sus secciones.", "Dibuja de memoria la estructura mínima de un programa y explica el propósito de cada parte.", "Ubica datos, código y punto de entrada en un programa mínimo.", ("introducción al lenguaje ensamblador", "entorno básico")),
            Topic("Registros y organización de la CPU", "Distinguir registros de propósito general, segmento y pila según su función.", "Clasifica EAX, ESP, EBP y un registro de segmento sin consultar apuntes.", "Justifica qué registro usarías para datos, direccionamiento y control de pila.", ("registros", "uso de registros", "fundamentos del lenguaje de máquina")),
            Topic("Datos, constantes y tamaños", "Relacionar BYTE, WORD y DWORD con tamaño, representación y compatibilidad de operandos.", "Explica el tamaño de cada tipo y predice qué movimientos son inválidos.", "Corrige tres movimientos entre operandos de tamaños incompatibles.", ("tipos de datos", "definición de datos", "constantes")),
            Topic("Instrucciones y procedimientos", "Analizar instrucciones de transferencia y el contrato de procedimientos de E/S.", "Explica qué hace MOV y diferencia READDEC, WRITESTRING, WRITEBIN y DUMPREGS.", "Diseña un programa corto que lea, muestre y verifique datos en registros.", ("instrucciones de transferencia", "constantes e instrucciones", "assembler")),
        ),
    ),
    "ELE1": CourseSpec(
        code="ELE1",
        name="Electrónica",
        exam_evidence="Primer Evaluación Ordinaria publicada en la semana 4.",
        topics=(
            Topic("Semiconductores y diodos", "Explicar el comportamiento básico de un semiconductor y un diodo en un circuito.", "Describe polarización directa e inversa, y qué evidencia esperarías al medir un diodo.", "Predice qué sucede con un diodo ante una fuente y resistencia dadas.", ("semiconductores", "diodos")),
            Topic("Rectificación", "Diferenciar rectificación de media onda, onda completa y configuraciones con diodos.", "Compara las formas de onda y el recorrido de corriente en cada caso.", "Traza la salida esperada y explica qué diodos conducen en cada semiciclo.", ("rectificación", "rectificador", "circuitos con diodos")),
            Topic("Análisis y medición de circuitos", "Resolver un circuito de diodos justificando cada supuesto y medición.", "Enumera los pasos para decidir el estado de cada diodo antes de calcular voltajes.", "Analiza un ejemplo nuevo y contrasta el resultado con una medición de multímetro o simulación.", ("análisis de circuitos", "medición", "ejemplo")),
            Topic("Recortadores", "Explicar cómo un recortador modifica una señal y de qué depende su nivel de corte.", "Explica el recorrido de corriente cuando la señal entra en la región de recorte.", "Predice y dibuja la salida de un recortador ante una entrada senoidal.", ("recortadores",)),
        ),
    ),
    "SINF": CourseSpec(
        code="SINF",
        name="Sistemas de Información Gerencial",
        exam_evidence="Corte actual: contenidos de las primeras unidades publicados en la fuente académica.",
        topics=(
            Topic("Dato, información y decisión", "Distinguir dato, información y conocimiento en un contexto de negocio.", "Convierte tres datos crudos en información útil para una decisión concreta.", "Propón un indicador y explica qué decisión habilita.", ("la información", "dato a la decisión", "datos")),
            Topic("Sistemas de información y SIG", "Definir un sistema de información y el propósito específico de un SIG.", "Explica componentes, entradas, procesamiento, salidas y retroalimentación.", "Modela un SI sencillo para un proceso real de una organización.", ("sistema de información gerencial", "sistema de información (si)", "los sistemas de información")),
            Topic("Áreas funcionales y rol estratégico", "Relacionar los SI con las áreas funcionales y la estrategia organizacional.", "Compara cómo ventas, operaciones y finanzas usan información diferente.", "Defiende una inversión en SI para un caso y explica su impacto estratégico.", ("áreas funcionales", "rol y clasificación", "motor de los negocios")),
            Topic("Clasificación y gestión de información", "Clasificar SI y argumentar cómo se gestiona la información para apoyar decisiones.", "Clasifica un sistema por nivel organizacional y tipo de decisión.", "Diseña un flujo de información con responsable, fuente, control y resultado.", ("clasificación", "gestión de la información", "funciones")),
        ),
    ),
    "ADCC": CourseSpec(
        code="ADCC",
        name="Administración de Centros de Cómputo",
        exam_evidence="Unidad 1: La nueva visión de la administración y tendencias administrativas modernas.",
        topics=(
            Topic("Nueva visión de la administración", "Explicar qué cambia en la visión administrativa moderna y sus consecuencias para un centro de cómputo.", "Contrasta una práctica administrativa tradicional con una visión moderna.", "Propón una decisión administrativa y justifica por qué responde a esa nueva visión.", ("nueva visión", "generalidades administración")),
            Topic("Interacción e interdependencia", "Distinguir interacción e interdependencia entre áreas y procesos.", "Explica con tus palabras por qué una decisión local puede afectar a todo el sistema.", "Mapea tres áreas y dos dependencias críticas de un centro de cómputo.", ("interacción", "interdependencia")),
            Topic("Efectos en cadena", "Analizar causas, consecuencias y retroalimentaciones de una modificación organizacional.", "Reconstruye una cadena causa → efecto → efecto secundario de memoria.", "Evalúa un cambio de recursos y anticipa tres impactos, incluidos riesgos.", ("efectos en cadena",)),
            Topic("Determinación de la interacción", "Aplicar un método explícito para identificar relaciones entre elementos organizacionales.", "Enumera las preguntas que usarías para detectar dependencias relevantes.", "Realiza un análisis breve de interacción para un incidente de TI realista.", ("determinación de la interacción",)),
        ),
    ),
}


def _normalized(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn")


def _course_code(folder: Path) -> str:
    return folder.name.split("-", 1)[0].upper()


def _note_link(vault: Path, note: Path, label: str) -> str:
    relative = note.relative_to(vault).with_suffix("").as_posix()
    return f"[[{relative}|{label}]]"


def _find_source(vault: Path, course: Path, topic: Topic) -> str:
    candidates = sorted(
        (path for path in course.rglob("*.md") if path.name.lower() not in {"index.md"} and "ultradocumentbody" not in path.name.lower()),
        key=lambda path: path.as_posix().lower(),
    )
    normalized_paths = [(_normalized(path.as_posix()), path) for path in candidates]
    for keyword in topic.keywords:
        needle = _normalized(keyword)
        for path_text, path in normalized_paths:
            if needle in path_text:
                return _note_link(vault, path, topic.title)
    return _note_link(vault, course / "index.md", f"Índice de {course.name}")


def _generic_spec(course: Path) -> CourseSpec:
    label = course.name
    return CourseSpec(
        code=_course_code(course),
        name=label,
        exam_evidence="Alcance por confirmar con la publicación oficial del curso.",
        topics=(Topic("Fundamentos publicados", "Explicar los conceptos esenciales publicados en el curso.", "Define el concepto principal sin apuntes.", "Aplica el concepto a un caso distinto.", tuple()),),
    )


def _project_brief(spec: CourseSpec, sources: list[str]) -> str:
    briefs = {
        "LEMA": (
            "Laboratorio de programas Assembler",
            "Construir y explicar programas pequeños que usen secciones, registros, tipos de datos e instrucciones de E/S.",
            "Un conjunto de tres programas propios: entrada/salida decimal, visualización de registros y validación de movimientos/tamaños.",
        ),
        "ELE1": (
            "Cuaderno de análisis de circuitos con diodos",
            "Resolver circuitos de diodos y contrastar la predicción con una simulación o medición disponible.",
            "Cuatro hojas de análisis: polarización, media onda, onda completa y recortador; cada una con supuesto, recorrido de corriente, salida esperada y verificación.",
        ),
        "SINF": (
            "Caso de decisión basada en información",
            "Transformar datos de un negocio en información útil y justificar el SI que apoya una decisión.",
            "Un caso de una página con datos de entrada, proceso, indicador, decisión, área funcional involucrada y control de calidad de información.",
        ),
        "ADCC": (
            "Mapa sistémico de un centro de cómputo",
            "Analizar interacción, interdependencia y efectos en cadena antes de proponer una decisión administrativa.",
            "Un mapa de áreas, dependencias, un cambio propuesto y tres consecuencias trazables, incluido un riesgo y una mitigación.",
        ),
    }
    title, purpose, deliverable = briefs.get(spec.code, ("Proyecto de dominio", "Aplicar los conceptos publicados a un caso nuevo.", "Una evidencia propia de aplicación y justificación."))
    references = "\n".join(f"- {source}" for source in sources)
    return (
        f"# {spec.code} — Proyecto de dominio\n\n"
        f"> Proyecto de práctica propio; no sustituye ni se entrega como una actividad evaluada.\n\n"
        f"## {title}\n\n"
        f"**Propósito:** {purpose}\n\n"
        f"**Entregable de práctica:** {deliverable}\n\n"
        "## Criterio de cierre\n\n"
        "- [ ] Puedo explicar cada decisión sin leer el material.\n"
        "- [ ] Puedo aplicar el modelo a un ejemplo distinto.\n"
        "- [ ] Identifiqué una limitación, un riesgo o una excepción.\n"
        "- [ ] Comparé mi evidencia con las fuentes configuradas, sin copiarlas ni sustituirlas.\n\n"
        "## Fuentes del corte\n\n"
        f"{references}\n\n"
        "## Registro de avances\n\n"
        "- Próximo paso:\n- Evidencia producida:\n- Duda que debo validar:\n"
    )


def _diagnostic(spec: CourseSpec, sources: list[str]) -> str:
    sections = []
    for number, (topic, source) in enumerate(zip(spec.topics, sources), start=1):
        sections.append(
            f"## {number}. {topic.title}\n\n"
            f"**Fuente:** {source}\n\n"
            f"1. Sin consultar material, responde: ¿qué significa este tema y por qué importa?\n"
            f"2. {topic.retrieve}\n"
            f"3. {topic.apply}\n\n"
            "**Autoevaluación:** `0` no respondo · `1` reconozco términos · `2` explico relaciones · `3` aplico y justifico.\n"
        )
    return "\n".join(sections)


def _guide(spec: CourseSpec, sources: list[str]) -> str:
    sessions = []
    for number, (topic, source) in enumerate(zip(spec.topics, sources), start=1):
        sessions.append(
            f"## Sesión {number} — {topic.title} (25–40 min)\n\n"
            f"**Resultado observable:** {topic.objective}\n\n"
            f"**Fuente primaria:** {source}\n\n"
            "1. **Diagnóstico (3 min):** responde las tres preguntas del bloque correspondiente de la prueba sin abrir la fuente.\n"
            "2. **Estudio focalizado (12–18 min):** lee/observa la fuente y anota solo definiciones, relaciones, condiciones y un ejemplo.\n"
            f"3. **Recuperación (5 min):** {topic.retrieve}\n"
            f"4. **Aplicación (8–12 min):** {topic.apply}\n"
            "5. **Cierre (2 min):** registra una duda, una corrección y la evidencia de comprensión en la bitácora.\n"
        )
    return "\n".join(sessions)


def _write_course_pack(
    vault: Path,
    root: Path,
    course: Path,
    *,
    source_provider: str = "blackboard_ultra",
    source_instance: str = "default",
) -> tuple[str, str, str]:
    spec = SPECS.get(_course_code(course), _generic_spec(course))
    sources = [_find_source(vault, course, topic) for topic in spec.topics]
    prefix = spec.code
    project_root = vault / STUDY_PROJECTS_DIR / f"{prefix} - Parcial 1"
    project_root.mkdir(parents=True, exist_ok=True)
    diagnostic_path = project_root / "Prueba diagnóstica.md"
    guide_path = project_root / "Guía de estudio.md"
    log_path = project_root / "Bitácora de dominio.md"
    project_path = project_root / "Proyecto de dominio.md"
    source_ref = course.relative_to(vault).as_posix()
    source_label = "la fuente académica" if source_provider == "blackboard_ultra" else source_provider
    source_link_label = "Índice de la fuente académica" if source_provider == "blackboard_ultra" else f"Índice {source_provider}"
    source_fields = (
        f'course: "{spec.name}"\ncheckpoint: "Parcial 1"\nnote_kind: study_checkpoint\nsource_provider: "{source_provider}"\n'
        f'source_instance: "{source_instance}"\nsource_ref: "[[{source_ref}/index|{source_link_label}]]"\n'
    )

    diagnostic_path.write_text(
        f"---\n{source_fields}---\n\n"
        f"# {spec.code} — Prueba diagnóstica del corte\n\n"
        f"> Propósito: medir comprensión inicial, no obtener una nota. Responde sin consultar fuentes y después revisa los vacíos.\n\n"
        f"**Alcance observado:** {spec.exam_evidence}\n\n"
        "**Tiempo sugerido:** 45–60 minutos. Escribe razones, no solo definiciones. No mires respuestas durante el primer intento.\n\n"
        + _diagnostic(spec, sources)
        + "\n## Resultado del diagnóstico\n\n- Puntaje por bloque (0–3):\n- Total: `/12`\n- Bloques con 0–1 (prioridad):\n- Primer error o duda que debo corregir:\n- Fecha del segundo intento:\n",
        encoding="utf-8",
        newline="\n",
    )
    guide_path.write_text(
        f"---\n{source_fields}---\n\n"
        f"# {spec.code} — Guía de estudio del corte\n\n"
        f"> Esta guía cubre evidencia publicada para el corte actual. {spec.exam_evidence} Si el docente publica un temario distinto, la fuente oficial configurada prevalece y se actualiza el checkpoint.\n\n"
        "## Método para aprobar y dominar\n\n"
        "Un bloque no se marca como dominado hasta que puedes **explicarlo sin apuntes**, **resolver/aplicar un caso nuevo** y **señalar una condición, límite o duda**.\n\n"
        + _guide(spec, sources)
        + "\n## Simulación antes del examen\n\n"
        "1. Repite la prueba diagnóstica sin fuentes.\n2. Convierte cada respuesta de 0–1 en una tarjeta de recuperación.\n3. Resuelve/aplica un caso nuevo por bloque.\n4. Pide a Hermes que evalúe tu explicación contra la fuente enlazada; no pidas la respuesta antes de intentar.\n5. Registra el resultado en la bitácora.\n",
        encoding="utf-8",
        newline="\n",
    )
    if not log_path.exists():
        log_path.write_text(
            f"# {spec.code} — Bitácora de dominio\n\n"
            "| Fecha | Bloque | Explicación sin apuntes (0–3) | Aplicación (0–3) | Error/duda concreta | Próxima acción | Próximo repaso |\n"
            "|---|---|---:|---:|---|---|\n"
            + "\n".join(f"|  | {topic.title} |  |  |  |  |  |" for topic in spec.topics)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    registry_path = project_root / "Registro de diagnósticos.md"
    if not registry_path.exists():
        registry_path.write_text(
            "# Registro de diagnósticos\n\n"
            "> Completa este registro después de intentar cada diagnóstico. El generador lo conserva una vez creado.\n\n"
            "| Fecha | Intento | Bloque | Explicación | Aplicación | Evidencia de aplicación | Duda |\n"
            "|---|---|---|---:|---:|---|---|\n"
            + "\n".join(f"|  | Inicial | {topic.title} |  |  |  |  |\n|  | Segundo | {topic.title} |  |  |  |  |" for topic in spec.topics)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    project_path.write_text(_project_brief(spec, sources), encoding="utf-8", newline="\n")
    (project_root / "AGENTS.md").write_text(
        f"# {spec.name} — contexto dedicado de estudio\n\n"
        f"Este proyecto es exclusivamente para preparar el Parcial 1 de **{spec.name}**.\n\n"
        f"## Fuente de verdad\n\n"
        f"- Fuente local ({source_label}): `../../{source_ref}/`\n"
        f"- No inventes alcance de examen ni fechas: usa solo publicaciones verificables de la fuente configurada.\n\n"
        "## Método\n\n"
        "- Antes de explicar, pide o plantea un intento de recuperación activa.\n"
        "- Evalúa explicación, aplicación y límites; no entregues respuestas listas para actividades calificadas.\n"
        "- Mantén la conversación limitada a esta materia y sus fuentes enlazadas.\n\n"
        "## Fuera de alcance\n\n"
        "- Otras materias, calificaciones y entrega/publicación en la plataforma académica.\n",
        encoding="utf-8",
        newline="\n",
    )
    return spec.code, project_root.relative_to(vault).as_posix()


def build_exam_checkpoint(vault: Path) -> CheckpointResult:
    vault = Path(vault)
    source = load_source_configs(vault)[0]
    source_root = vault / source.root
    blackboard = source_root
    root = vault / "Control Académico" / CHECKPOINT_DIR
    root.mkdir(parents=True, exist_ok=True)
    courses = sorted((course for course in blackboard.iterdir() if course.is_dir() and (course / "index.md").is_file()), key=lambda path: path.name)
    # Migration: remove only legacy generated course packs from the shared panel.
    for course in courses:
        spec = SPECS.get(_course_code(course), _generic_spec(course))
        for suffix in ("Prueba diagnóstica", "Guía de estudio", "Bitácora de dominio", "Proyecto de dominio"):
            legacy = root / f"{spec.code} - {suffix}.md"
            if legacy.is_file():
                legacy.unlink()
    rows = [
        _write_course_pack(
            vault,
            root,
            course,
            source_provider=source.provider,
            source_instance=source.instance,
        )
        for course in courses
    ]
    panel = root / "00 - Panel del corte.md"
    panel.write_text(
        "# Checkpoint — Parcial 1\n\n"
        "> Índice de los cortes de unidades. Cada materia abre en su propio proyecto de estudio para que las conversaciones, archivos de trabajo y reglas no se mezclen.\n\n"
        "## Cómo usarlo\n\n"
        "1. Abre únicamente el proyecto de la materia que estudiarás.\n"
        "2. Resuelve su prueba diagnóstica **sin consultar fuentes**.\n"
        "3. Prioriza los bloques con puntuación 0–1 y registra evidencia de recuperación y aplicación.\n"
        "4. Repite la prueba antes del parcial.\n\n"
        "## Proyectos dedicados por materia\n\n"
        + "\n".join(f"- **{code}:** [[{project}/Prueba diagnóstica|Prueba diagnóstica]] · [[{project}/Guía de estudio|Guía de estudio]] · [[{project}/Proyecto de dominio|Proyecto de dominio]]" for code, project in rows)
        + "\n\n## Aislamiento de contexto\n\n"
        "Cada proyecto vive bajo `Proyectos de Estudio/<curso> - Parcial 1/` y tiene su propio `AGENTS.md`. Ese archivo limita la sesión a la materia, su fuente configurada y el método de recuperación activa. No incluye instrucciones de otras materias ni de calificaciones.\n\n"
        "## Límite de capacidad\n\n"
        "Durante semana de parciales, no intentes completar todos los bloques en un día. Cierra primero la entrega con fecha real más cercana; después, un bloque prioritario por sesión. Deja explícitamente para después los bloques sin fecha inmediata.\n",
        encoding="utf-8",
        newline="\n",
    )
    return CheckpointResult(root=root, course_count=len(courses), panel_path=panel)
