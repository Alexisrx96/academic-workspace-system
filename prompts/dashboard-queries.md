# Consultas del dashboard académico para Hermes

Estas consultas usan la salida de:

```bash
uv run python scripts/dashboard_snapshot.py --target D:/path/to/vault
```

## Reglas comunes

- Trata `Blackboard/` o cualquier `source` configurada como fuente académica, no como memoria implícita.
- No inventes fechas, alcance de examen, calificaciones ni requisitos.
- Distingue hechos del snapshot, inferencias y recomendaciones.
- Si `health.sync_status` no es `verified`, dilo explícitamente.
- Prioriza una sola acción sostenible; no produzcas una lista ilimitada.
- Para explicar un tema, pide primero un intento de recuperación activa.
- No entregues respuestas listas para actividades calificadas.

## ¿Qué debo hacer hoy?

1. Lee `attention`.
2. Prioriza, en este orden:
   - entrega con fecha explícita;
   - fecha que requiere confirmación;
   - alerta de fuente desactualizada/no disponible;
   - bloque de dominio `0–1/3`;
   - publicación nueva.
3. Si hay empate, elige una sola acción y justifica por qué.
4. Devuelve:
   - prioridad;
   - fuente/ruta;
   - acción concreta de 25 minutos;
   - criterio de cierre.

## Dame una sesión de 25 minutos

1. Elige un único elemento de `attention` o `domain`.
2. Formula tres preguntas de diagnóstico antes de explicar.
3. Divide la sesión en diagnóstico, comprensión, recuperación, aplicación y cierre.
4. Incluye una evidencia observable y una duda/límite que registrar.

## ¿Qué debo confirmar?

1. Filtra acciones que comiencen con `Confirmar`.
2. Lista la fecha textual y su fuente.
3. Indica que no es una fecha de calendario confirmada.
4. No la conviertas en una fecha oficial.

## Evalúa mi explicación

1. Pide al estudiante que responda primero.
2. Compara su respuesta con la fuente enlazada y el tema seleccionado.
3. Evalúa:
   - exactitud;
   - relaciones causales;
   - aplicación a un caso nuevo;
   - límites, condiciones o excepciones.
4. Devuelve correcciones concretas, no una respuesta completa previa al intento.

## Próxima acción técnica

Cuando una consulta dependa de datos actuales, ejecuta o solicita regenerar el snapshot. No uses una respuesta anterior como si fuera el estado actual de la bóveda.
