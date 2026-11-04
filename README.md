# Blackboard UTEC → Obsidian (determinista)

Sincroniza **solo de lectura** desde `https://utecvirtual.blackboard.com/` hacia esta bóveda.

## Alcance confirmado

- Materias disponibles.
- Contenido y módulos de curso, recursivamente.
- Actividades y sus fechas de entrega publicadas.
- Anuncios.
- Retroalimentación textual del docente, cuando Blackboard la expone.
- **Excluye calificaciones**: no se descargan, calculan, agregan ni convierten a decisiones.

La salida es determinista: orden canónico por identificadores de Blackboard, nombres de archivo estables, escritura atómica, mapa fuente→destino y manifiesto SHA-256. Antes de escribir, la sincronización compara el mapa vivo con el mapa anterior y valida los hashes locales; dos ejecuciones con la misma fuente no modifican ni descargan archivos.

## Autenticación: cookie de la sesión del navegador

La única ruta de sincronización usa la cookie de la sesión autenticada de Chrome para llamar los endpoints JSON que Blackboard Ultra usa internamente. No utiliza API key, application key/secret ni `user`/`pass`.

1. Abre el perfil controlable de Chrome e inicia sesión manualmente en Blackboard. El programa no consume `user`/`pass` ni intenta iniciar sesión.
2. Ejecuta desde esta carpeta:

```bash
# Construye el mapa origen→destino y muestra el diferencial sin escribir ni descargar.
uv run --extra browser academic-workspace --target D:/path/to/vault --plan

# Solo descarga/renderiza si el mapa o los hashes locales requieren una actualización.
uv run --extra browser academic-workspace --target D:/path/to/vault
```

`--plan` (también disponible como `--dry-run`) informa cursos, elementos, altas/cambios/bajas, una vista previa de archivos (`create`/`update`/`delete`), integridad y si se necesitan descargas. La ejecución normal escribe `Blackboard/`, `.blackboard-sync/source-map.json` y `.blackboard-sync/manifest.json` únicamente cuando hace falta; en un estado limpio informa `sin cambios y sin descargas`. Si el perfil está en otra ruta, se indica explícitamente con `--profile C:/ruta/al/perfil`; también puede exponerse como `ACADEMIC_WORKSPACE_BROWSER_PROFILE` en el entorno.

La sincronización busca automáticamente una sesión DevTools autenticada en los navegadores/perfiles disponibles y valida la sesión contra Blackboard. No depende del nombre del perfil. `--profile` y `ACADEMIC_WORKSPACE_BROWSER_PROFILE` son únicamente overrides opcionales para entornos donde haya varios endpoints.

Si no encuentra una sesión, puedes pedirle que lance un Chrome controlado con un perfil separado:

```bash
uv run --extra browser academic-workspace \
  --target D:/path/to/vault \
  --plan \
  --launch-browser
```

En una ejecución normal, si la vista previa contiene eliminaciones o escrituras fuera de las raíces permitidas, el programa muestra el motivo y solicita escribir `si` antes de continuar. Para automatizaciones no interactivas, usa `--yes` únicamente después de revisar el resultado de `--plan`; una cancelación devuelve código 3 y no aplica cambios.

El comando solo lanza el navegador y termina con código 3. Debes iniciar sesión manualmente en Blackboard y volver a ejecutar el comando; nunca introduce credenciales ni reemplaza el navegador personal.

### Configuración portable

El código no depende de una bóveda, usuario ni curso personal. La configuración de fuentes de la bóveda vive en `.blackboard-sync/sources.json`; si no existe, se usan valores neutros compatibles con una instalación nueva. Copia `academic-workspace.example.json` como referencia para una configuración compartible.


Las rutas personales deben proporcionarse mediante argumentos o variables de entorno, especialmente:

```bat
set ACADEMIC_WORKSPACE_BROWSER_PROFILE=C:\Users\<user>\AppData\Local\CuaDriver\BrowserProfiles\academic-workspace-live
```

No se deben publicar `sources.json`, perfiles del navegador, cookies, apuntes, trabajos ni la carpeta `.blackboard-sync` de una bóveda personal.

### Comandos humanos

```bash
academic-workspace init --target D:/path/to/vault
academic-workspace config validate --target D:/path/to/vault
academic-workspace status --target D:/path/to/vault
academic-workspace report --target D:/path/to/vault
academic-workspace rollback --target D:/path/to/vault
academic-workspace study start --target D:/path/to/vault --course FIS1 --topic "Cinemática" --objective "Validar procedimiento" --mode explicit_validation
academic-workspace study list --target D:/path/to/vault
academic-workspace study status --target D:/path/to/vault --session-id "session:..."
academic-workspace study complete --target D:/path/to/vault --session-id "session:..."
academic-workspace study search --target D:/path/to/vault --query "ejemplo de interdependencia" --authorized
academic-workspace study fetch-url --target D:/path/to/vault --url "https://example.org/page" --purpose find_examples --authorized --quote "Texto literal que aparece en la página"
academic-workspace study claim --target D:/path/to/vault --source-id "external-source:..." --claim "Afirmación" --quote "Texto literal" --verdict externally_confirmed
academic-workspace study math-formalize --target D:/path/to/vault --course FIS1 --topic "Cinemática" --source-ref "Blackboard/FIS1/Cinematica.md" --script-file "Cálculos/propuesta.phs"
academic-workspace study math-formalize --target D:/path/to/vault --course FIS1 --topic "Cinemática" --source-ref "Blackboard/FIS1/Cinematica.md" --script-file "Cálculos/propuesta.phs" --approved
academic-workspace study validate-math --target D:/path/to/vault --script "FIS1/Validaciones/cinematica_01.phs" --student-value 20 --units "m/s" --topic "cinemática"
academic-workspace study validate --target D:/path/to/vault --course-claim "..." --external-claim "..." --relationship conflict --external-evidence
academic-workspace doctor --target D:/path/to/vault
```

Cada `study start` crea una ocurrencia nueva, incluso si curso, tema y objetivo coinciden con una sesión anterior. Los cambios de estado conservan revisión y timestamps; `pause`/`resume` sobreviven a un reinicio del proceso. `study list` proyecta una sola fila con el último estado de cada ocurrencia. Una sesión no puede completarse hasta que exista al menos un intento del estudiante en su fase actual.

### Panel local de estudio

```bash
uv run python ui/server.py --target D:/path/to/vault --host 127.0.0.1 --port 8765
```

Abre `http://127.0.0.1:8765/`. El panel muestra sesiones activas o pausadas, permite abrirlas por URL, recargarlas, pausarlas y reanudarlas. El servidor acepta únicamente `Host` local, rechaza orígenes externos, exige JSON para mutaciones, no habilita CORS y sanitiza el HTML derivado de Markdown. No lo expongas en una interfaz de red pública ni cambies `--host` a una dirección externa.

La configuración es fail-closed: si `workspace-config.json` o `sources.json` existe pero está corrupto, `config validate` lo reporta como inválido en vez de activar defaults silenciosamente. Las raíces de fuentes deben permanecer dentro de la bóveda.

`init` es idempotente: crea la configuración neutral solo si no existe. `status` devuelve salud de sincronización, fuentes, índices y reportes. `doctor` agrega verificaciones de escritura, configuración, índices y candidatos DevTools.

`report` devuelve un resumen JSON versionado (`execution-summary.v1`) con el estado de la ejecución, artefactos encontrados, verificaciones disponibles, fuentes configuradas, evidencia faltante y riesgos detectados. El flujo diferencial escribe automáticamente `.blackboard-sync/generation-report.json` y `.blackboard-sync/execution-summary.json` al terminar, incluso cuando no requiere descargas. También escribe `execution-verification.json` después de una ejecución y conserva el último backup en `.blackboard-sync/backups/latest/`. Si la verificación posterior queda bloqueada, el proceso devuelve código 4 y puede revertirse con `academic-workspace rollback --target ...`. Devuelve código 3 cuando el usuario cancela la confirmación.

La memoria usa SQLite por defecto en workspaces inicializados:

```text
.blackboard-sync/memory.sqlite3
```

El backend conserva `append_once`, registra `schema_version` e importa automáticamente eventos del legado `.blackboard-sync/evidence.jsonl`. Para compatibilidad temporal puede seleccionarse `memory.backend: "jsonl"`; la memoria no decide prioridades académicas ni modifica resultados manuales.

`generation-report.json` mantiene un inventario verificable de cada archivo observado: tamaño y SHA-256. El reporte compara hashes desde su primera ejecución con el esquema `generation-report.v1.1`, detecta cambios aunque el archivo conserve el mismo tamaño y conserva compatibilidad de lectura con reportes antiguos basados únicamente en tamaño. Si detecta escrituras fuera de las raíces permitidas, devuelve `status: "blocked"` y enumera las rutas inesperadas.

### Kernel público de aplicación

```python
from academic_workspace import AcademicWorkspaceKernel

kernel = AcademicWorkspaceKernel("D:/path/to/vault")
status = kernel.status()
context = kernel.study_context()
results = kernel.search("sistemas de información")
```

El kernel agrupa configuración, diagnóstico, estado, memoria, búsqueda, RAG, GraphRAG, evidencia y reportes. CLI y MCP quedan como adaptadores; Blackboard, SQLite, JSONL y Obsidian permanecen en capas reemplazables. Esto prepara la siguiente fase de API HTTP sin duplicar la lógica académica.

### Herramienta preferida para matemáticas y física: PHS

El workspace declara `phs` (PhysureScript) como motor preferido, pero opcional, para verificar cálculos y modelos de matemáticas, cálculo y cualquier área de física: electricidad, electrónica, circuitos, cinemática, dinámica, mecánica, fluidos, sólidos, termodinámica, óptica, ondas y electromagnetismo. Si no está instalado, `doctor` lo reporta como advertencia con una sugerencia de instalación; no se instalan herramientas automáticamente.

La sugerencia no bloquea una sesión ni sustituye la explicación. Cuando el problema sea apto para formalización, el agente debe intentar usar PHS si existe un script o puede construir una formulación verificable; debe separar el resultado calculado, la explicación y los supuestos.

```bash
academic-workspace phs suggest --target D:/path/to/vault "calcular la corriente en un circuito RC"
academic-workspace phs check --target D:/path/to/vault
academic-workspace phs run --target D:/path/to/vault "02 - Cursos/ELE1/guia1.phs"
academic-workspace phs transpile --target D:/path/to/vault "02 - Cursos/ELE1/guia1.phs" --language python
```

MCP expone `check_math_physics_engine` y `run_phs_script`. Para respuestas matemáticas o físicas, el agente debe preferir PHS cuando exista un script verificable; la respuesta debe distinguir entre resultado calculado por PHS, razonamiento explicativo y supuestos del modelo.

## Archivos, estructura y validación

Todo recurso alojado en Blackboard y referenciado desde contenido se conserva junto a la nota que lo publica:

```text
Blackboard/<curso>/Contenido/<carpeta o lección Blackboard>--<id>/
├── index.md                         # nota del contenedor Blackboard
├── <contenido>--<id>.md             # recurso/actividad hijo
└── Adjuntos/
    ├── <archivo>--<id>.pdf          # original descargado
    ├── <archivo>--<id>.pdf.md       # Markdown estructurado por página
    ├── <archivo>--<id>.docx         # original descargado
    └── <archivo>--<id>.docx.md      # Markdown estructurado por encabezados/tablas
```

Cada carpeta o lección de Blackboard se representa como su propia carpeta local con `index.md`; los descendientes conservan esa jerarquía. PDF y DOCX se transforman a Markdown con metadatos YAML deterministas (`source_file`, `source_format`, `extraction`), título y secciones; el binario original no se sustituye. Los demás adjuntos observados (por ejemplo imágenes) también se conservan. Un PDF sin capa de texto queda marcado para OCR; si se añade o corrige una extracción OCR al `.pdf.md`, la sincronización la conserva mientras el PDF no haya cambiado.

Comprueba contra Blackboard que el mapa actual coincide con la plataforma, que cada carpeta/lección tiene su `index.md`, que el número de adjuntos coincide con disco, que cada adjunto pertenece a una nota de contenido, que existen sidecars PDF/DOCX con formato válido y que cada hash del manifiesto coincide:

```bash
uv run --extra browser python scripts/verify_sync.py \
  --target D:/path/to/vault \
  --profile C:/Users/<user>/AppData/Local/CuaDriver/BrowserProfiles/academic-workspace-live
```

## Validación matemática y física con PHS

Para problemas cuantitativos, `validate-math` recomienda fuertemente PhysureScript (PHS) y compara el resultado del estudiante con la salida del script. La ausencia de PHS se reporta como `phs_unavailable`; no se presenta una validación manual como si fuera equivalente.

```bash
academic-workspace study validate-math \
  --target D:/path/to/vault \
  --script "FIS1/Validaciones/cinematica_01.phs" \
  --student-value 20 \
  --units "m/s" \
  --topic "cinemática"
```

Estados principales: `verified`, `unit_mismatch`, `calculation_mismatch`, `formalization_uncertain`, `script_failed` y `phs_unavailable`. La salida separa el resultado de PHS, el resultado del estudiante, las unidades, la recomendación del motor y las limitaciones.

## Control semanal, calendario y comprensión

Desde Windows, ejecuta `Control-Semanal.bat`. Este BAT realiza una sincronización diferencial y, solo si la sesión Chrome de Blackboard está disponible, actualiza:

```text
Control Académico/
├── 00 - Dashboard académico.md           # portada académica accionable
├── Estado semanal.md                    # pendientes, fechas textuales y publicaciones nuevas
├── Recordatorios.md                     # lista breve de entregas publicadas
├── Matriz de dominio.md                 # vista agregada de bitácoras por curso
├── UTEC-Fechas.ics                      # calendario importable con alerta 24 h antes
└── Comprensión/
    ├── Guía para estudiar con Hermes.md
    └── Mi registro de comprensión.md
```

El estado técnico de frescura se guarda en `.blackboard-sync/sync-health.json`. Una actualización local solo cambia `last_local_refresh`; `last_blackboard_sync` y `sync_status: verified` se escriben únicamente cuando `Control-Semanal.bat` completa la sincronización de Blackboard. Si esa sincronización falla, el control marca `unavailable` y conserva la última sincronización válida.

La primera ejecución crea una **línea base** para no alertar masivamente sobre el material histórico. Las siguientes comparan hashes de notas Blackboard y muestran únicamente publicaciones nuevas o modificadas, filtrando índices contenedores y artefactos técnicos como `ultraDocumentBody` para que una publicación no aparezca varias veces. Las fechas escritas dentro del texto se muestran en `Estado semanal.md` como **pendientes de confirmación**, pero no se convierten automáticamente en eventos. Los eventos `.ics` se crean únicamente a partir de `due_at` que Blackboard haya expuesto: nunca se infieren fechas como eventos desde títulos o texto. `Matriz de dominio.md` agrega las filas de las bitácoras por materia y no modifica sus fuentes. Para importar el calendario en la aplicación predeterminada, ejecuta `Abrir-Calendario-UTEC.bat`.

Para actualizar solo el dashboard desde los datos locales —sin abrir Chrome ni contactar Blackboard— ejecuta `Actualizar-Dashboard-Local.bat`. Para programarlo cada 60 minutos usa `Instalar-Dashboard-Local.bat`; para retirarlo, `Desinstalar-Dashboard-Local.bat`. La tarea es segura para ejecutarse en segundo plano porque no sincroniza datos externos. `Control-Semanal.bat` sigue siendo el flujo completo que primero sincroniza Blackboard y luego regenera todas las vistas.

Para un recordatorio local diario del flujo completo, ejecuta una vez `Instalar-Recordatorio-Control.bat` y elige la hora —el valor por defecto es `18:30`. Esa tarea requiere Chrome con Blackboard autenticado; para retirarla, ejecuta `Desinstalar-Recordatorio-Control.bat`.

Para una tarea con nombre y propósito explícitos, usa `Instalar-Sincronizacion-Blackboard-Diaria.bat` y `Desinstalar-Sincronizacion-Blackboard-Diaria.bat`. Esta opción tampoco se instala automáticamente: requiere Chrome abierto y una sesión Blackboard válida.

En cada sesión de estudio, abre una nota Blackboard concreta y usa la guía de comprensión: diagnóstico breve, explicación desde la fuente, recuperación sin apuntes, ejemplo aplicado y una duda registrada. Este flujo está pensado para priorizar comprensión verificable sobre volumen cuando el tiempo disponible es limitado.

### Checkpoint de parciales

El mismo control genera un corte de unidades reproducible con un **proyecto Hermes separado por materia**. Cada proyecto contiene una prueba diagnóstica sin respuestas, una guía de sesiones de 25–40 minutos, una bitácora de dominio y un proyecto de práctica propio. Las fuentes son enlaces directos a `Blackboard/`; el generador no modifica esas fuentes ni presenta el material como temario oficial cuando el docente no lo ha declarado.

```text
Control Académico/Checkpoint - Parcial 1/
└── 00 - Panel del corte.md             # índice, no espacio de estudio compartido

Proyectos de Estudio/
├── LEMA - Parcial 1/
├── ELE1 - Parcial 1/
├── SINF - Parcial 1/
└── ADCC - Parcial 1/
    ├── AGENTS.md                       # alcance y reglas de esa materia solamente
    ├── Prueba diagnóstica.md
    ├── Guía de estudio.md
    ├── Bitácora de dominio.md
    └── Proyecto de dominio.md
```

Cada carpeta se registra como un Proyecto de escritorio Hermes independiente. Al abrir una sesión en uno de ellos, su `AGENTS.md` limita el contexto a la materia activa, la fuente Blackboard enlazada y el método de recuperación; las demás materias y sus reglas quedan fuera. Los proyectos de dominio son deliberadamente espacios separados de práctica (Assembler, circuitos, caso de SI y mapa sistémico), listos para crecer sin ensuciar una sesión dedicada a otra asignatura.

### Lecturas refinadas y entrelazadas

El control también genera, dentro de cada proyecto de materia, `Lecturas refinadas/`. Es una capa derivada de concentración que selecciona clases y documentos de unidades publicados, preserva la fuente original y:

- refluye texto compacto a párrafos legibles;
- conserva y ordena adjuntos como listas navegables;
- expone algunos rótulos ya presentes en la fuente como secciones Markdown;
- añade al final un resumen **extractivo** de frases publicadas, sin contenido externo; y
- enlaza lecturas del mismo curso que comparten terminología, marcándolo como conexión para validar durante el estudio.

`Blackboard/` no se edita: cada lectura refinada enlaza de vuelta a su fuente exacta. La capa se reconstruye de manera determinista en cada ejecución del control semanal.

## Blackboard como fuente y apuntes como espacio de trabajo

La sincronización no mezcla ni sobrescribe apuntes propios. El puente de conocimiento deja a `Blackboard/` como fuente de referencia y enlaza las carpetas de curso que ya existen en la raíz (`SINF/`, `ELE1/`) o crea un espacio inicial para las demás (`ADCC/`, `LEMA/`).

```text
Blackboard/<curso>/              # fuente sincronizada, gestionada por el sincronizador
SINF/ o ELE1/                    # apuntes, borradores y trabajos propios
<curso>/00 - Blackboard y apuntes.md
Control Académico/Mapa de conocimiento.md
```

Cada hub de curso lista tus notas existentes y enlaza de vuelta al `index.md` del curso en Blackboard. El mapa se actualiza al ejecutar `Control-Semanal.bat` y nunca edita notas propias; solo reescribe sus propios hubs generados.

Para enlazar un apunte específico a la fuente exacta, copia `Control Académico/Plantilla - Apunte vinculado.md` dentro de la carpeta del curso y completa:

```yaml
source_blackboard: "[[Blackboard/<curso>/<ruta>/index|Fuente exacta]]"
```

Esto crea un vínculo explícito y navegable en Obsidian entre material publicado, tu explicación, tu práctica y el trabajo que entregues. No se realizan asociaciones por similitud de título.

## Reporte de resultados y accionables

El control semanal genera `Control Académico/Reporte de resultados académicos.md` a partir de `Control Académico/Registro de resultados académicos.json`. El registro es manual y separado del sincronizador: Blackboard puede aportar actividades y retroalimentación textual, pero **no se convierte automáticamente en una calificación**.

Cada elemento puede representar una tarea, actividad, examen o laboratorio y admite estados como:

- `no_conformidad`
- `falta_preparacion`
- `no_entregado`
- `incompleto`
- `tarde`
- `entregado` o `completado`
- `en_revision`
- `resultado_desconocido`

Los estados problemáticos generan una acción concreta de estudio o seguimiento. Los estados satisfactorios generan recomendaciones, no tareas artificiales. Si una nota solo es visible para el líder de un grupo, se registra `score_visibility: "group_leader_only"` y no se infiere ningún resultado individual.

Ejemplo de registro:

```json
{
  "schema": "academic-results.v1",
  "items": [
    {
      "id": "sinf-proyecto-1",
      "course": "SINF",
      "title": "Proyecto grupal",
      "kind": "actividad",
      "status": "resultado_desconocido",
      "score": null,
      "score_origin": "lider_grupo",
      "score_visibility": "group_leader_only",
      "reason": "La nota solo está visible para el líder",
      "evidence": "Confirmar con el líder del grupo",
      "source_ref": "[[Blackboard/SINF/Proyecto grupal]]"
    }
  ]
}
```

Un resultado ausente no equivale a cero. Las fuentes externas, revisiones fuera de Blackboard y entregas grupales deben declarar su origen explícitamente.


## RAG citable y GraphRAG local

El proyecto incluye recuperación local sin invocar un modelo. Además de `lexical`, `semantic` y `hybrid`, `graph-hybrid` combina recuperación lexical con una expansión determinista del grafo académico:

```bash
uv run python scripts/build_rag_context.py \
  "¿Qué relación hay entre datos, información y decisiones?" \
  --target D:/path/to/vault \
  --mode graph-hybrid \
  --course EXAMPLE-V02-022026 \
  --max-chunks 8 \
  --max-chars 6000 \
  --format json
```

GraphRAG conserva primero la evidencia recuperada directamente y después añade vecinos del grafo dentro del presupuesto. Las relaciones tienen procedencia explícita:

- `explicit_link`: enlaces `source_ref`/WikiLink.
- `same_unit`: documentos cercanos dentro de la misma unidad Blackboard, generados determinísticamente y limitados a tres vecinos.
- `semantic_related`: sugerencias calculadas con embeddings, siempre con confianza y `model_id`.

La expansión se limita por curso, lane, número de saltos (`--graph-hops`) y número de nodos (`--graph-nodes`). El grafo es una proyección reconstruible en `.blackboard-sync/resource-registry.sqlite3`; no modifica `Blackboard/` ni las notas propias. Cada contexto marca las fuentes directas como `seed` y las expandidas como `graph`, manteniendo las citas `[S1]`, `[S2]`, etc.

## Pruebas

```bash
uv run --extra dev pytest -q
```
