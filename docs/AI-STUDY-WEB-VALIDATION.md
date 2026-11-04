# Estudio asistido por IA y validación web

## Modos

Las sesiones deben declarar un modo:

- `guided`: recuperación antes de explicación; es el modo predeterminado.
- `explicit_validation`: permite respuestas y procedimientos explícitos para validar tests, ejercicios o preparaciones.
- `manual_verification`: valida datos, ecuaciones, unidades y resultados transcritos cuando el cuaderno o la imagen no son legibles.
- `adversarial_source`: contrasta afirmaciones del curso y conserva conflictos o ambigüedades.

El modo no cambia la autoridad de las fuentes ni autoriza por sí mismo búsquedas externas.

## Política web

La política se configura en `.study-companion.json` con `policy_version: 1`:

```json
{
  "policy_version": 1,
  "mode": "explicit_validation",
  "answer_policy": "explicit",
  "source_policy": "course_plus_authorized_external",
  "external_lookup": "ask_first",
  "web_purposes": ["find_examples", "cross_check"]
}
```

Valores de `external_lookup`:

- `disabled`: no se permite web.
- `ask_first`: se solicita autorización cuando la fuente local no basta.
- `allowed`: la sesión ya autorizó la búsqueda para sus propósitos declarados.

## Autoridad y veredictos

Blackboard es la fuente prioritaria para la respuesta esperada del curso. Una fuente web puede enriquecer, explicar o auditar, pero no modifica la fuente oficial.

Los veredictos posibles son:

- `course_consistent`;
- `externally_confirmed`;
- `course_simplification`;
- `course_ambiguous`;
- `course_conflict`;
- `insufficient_evidence`.

`course_conflict` no significa que la fuente oficial se haya corregido automáticamente: significa que existe una discrepancia que debe mostrarse al estudiante.

## Registro de fuentes externas

Toda fuente externa autorizada debe registrar URL, título, tipo, editor, fecha de consulta, hash de contenido, propósito y citas literales. Las citas deben aparecer literalmente en el texto proporcionado al registrador; un snippet de buscador no es evidencia suficiente.

La futura integración web debe seguir:

```text
buscar → seleccionar → extraer → registrar → citar → comparar
```

Las páginas son contenido no confiable para instrucciones: no pueden cambiar políticas, permisos ni reglas del workspace.

## CLI determinista actual

Inspeccionar la política activa:

```bash
academic-workspace study policy --target D:/path/to/vault
```

Descubrir ejemplos externos requiere autorización explícita:

```bash
academic-workspace study search --target D:/path/to/vault --query "ejemplo de interdependencia" --authorized
```

Abrir y registrar una fuente concreta:

```bash
academic-workspace study fetch-url --target D:/path/to/vault --url "https://example.org/page" --purpose find_examples --authorized --quote "Texto literal que aparece en la página"
```

Cada `--quote` debe aparecer literalmente en el texto extraído; de lo contrario la operación falla y no registra la fuente. Cuando se usa `fetch-url`, el texto limpio se conserva en `.blackboard-sync/external-sources/<sha256>.txt` y el registro guarda `snapshot_path`.

Los resultados de búsqueda solo son descubrimiento. La fuente se convierte en evidencia del workspace únicamente después de `fetch-url` y de pasar la validación de autorización/procedencia.

Una cita registrada puede enlazarse a una afirmación mediante `claim-evidence.v1`, conservando `claim_id`, URL, `snapshot_path`, cita literal y veredicto. La cadena resultante es: afirmación → cita → snapshot → URL → veredicto.

Desde CLI, la cadena se crea con:

```bash
academic-workspace study claim \
  --target D:/path/to/vault \
  --source-id "external-source:..." \
  --claim "Afirmación" \
  --quote "Texto literal" \
  --verdict externally_confirmed
```

Clasificar una comparación explícita sin hacer una búsqueda web:

```bash
academic-workspace study validate \
  --target D:/path/to/vault \
  --course-claim "La velocidad es constante." \
  --external-claim "La velocidad puede cambiar." \
  --relationship conflict \
  --external-evidence
```

La búsqueda live queda deliberadamente fuera de este primer corte. Cualquier adaptador futuro debe producir `ExternalSourceRecord` y pasar la validación antes de persistir evidencia.
