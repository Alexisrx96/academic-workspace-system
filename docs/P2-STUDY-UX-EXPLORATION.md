# Exploración P2: experiencia, permisos y superficie de estudio

Esta fase no fija todavía una UI definitiva. Compara opciones reversibles.

## Opción A: CLI + chat estructurado

- Mantiene el kernel actual.
- `study start`, `preflight`, `ai-context`, `metrics`.
- La conversación presenta LaTeX, PHS y fuentes.
- Menor costo y máxima trazabilidad.

## Opción B: panel local de sesión

- Página local/desktop con fase activa, fuente, pregunta y acciones.
- Consume `ai-study-context.v1`.
- No contiene lógica académica propia.
- Requiere diseñar persistencia de UI y accesibilidad.

## Opción C: plugin de escritorio

- Integra sesión, archivos, diffs y permisos en Hermes Desktop.
- Buena experiencia de usuario.
- Mayor acoplamiento al producto y mayor costo de mantenimiento.

## Recomendación provisional

Usar A como contrato canónico y prototipar B como vista derivada. No implementar C hasta validar que la sesión estructurada, los permisos y el flujo PHS son estables.

## Permisos unificados propuestos

```text
read_official_source       permitido
search_web                 ask_first
fetch_external_source      ask_first
transform_notes_to_phs     ask_first
write_generated_phs        ask_first
execute_phs                ask_first
modify_user_note           ask_always
create_incident_report     permitido localmente
prepare_github_issue       permitido localmente
publish_github_issue       ask_always
publish_external_content   ask_always
```

Cada autorización debe mostrar alcance, archivos, fuentes, reversibilidad y destino externo.

## Métricas a validar antes de construir UI

- tiempo para iniciar una sesión;
- porcentaje de sesiones reanudadas;
- errores repetidos detectados;
- validaciones PHS completadas;
- sesiones con evidencia registrada;
- diferencia entre confianza y desempeño.
