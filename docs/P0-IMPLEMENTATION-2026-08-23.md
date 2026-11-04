# P0 implementation — continuity, confinement, export and local UI security

Date: 2026-08-23

## Scope

This vertical slice implements the blocking prerequisites identified by the academic-workspace introspection. It does not claim to complete the tutor/feedback/evidence product loop.

## Session continuity

- Every `study start` creates a distinct occurrence ID.
- Session snapshots carry `created_at`, `updated_at`, `ended_at`, and a monotonic `revision`.
- SQLite applies compare-and-append under `BEGIN IMMEDIATE`; concurrent transitions from the same revision cannot both commit.
- Projection prefers a terminal state when corrupt/legacy data contains equal-revision conflicts.
- Pause/resume transitions persist as distinct events and survive process/browser reloads.
- Attempts have occurrence IDs and `occurred_at`; identical responses are not collapsed.
- `study list` and `AcademicWorkspaceKernel.study_sessions()` project the latest state once per occurrence.
- Metrics count projected sessions, not state snapshots.
- Attempts require an active session and the current phase.
- Phase advancement requires an active session.
- Completion requires at least one student attempt.
- Legacy `study-session.v1` events remain readable with default revision/timestamp fields.

## Configuration and paths

- Missing config retains compatibility defaults.
- Explicit but malformed `workspace-config.json` or `sources.json` is invalid and reported fail-closed.
- Source roots are resolved and must remain below the workspace target.
- Generation-report allowed roots include configured sources and the declared work/control/external lanes.
- The current real workspace produces a safe generation projection with no unexpected paths.

## Sanitized export

- Exports are built in a staging directory and promoted only after all checks pass.
- Failed scans do not leave the requested output partially written.
- Symlinks that escape the project are rejected.
- Binary candidates are rejected because their privacy cannot be verified safely by the text scanner.
- Existing safe placeholders are preserved.
- Code is scanned without destructive path substitution; documentation/configuration text is sanitized.
- UI sources and frontend build metadata are included in the allowlisted template.
- Generated license text no longer hardcodes a personal name.
- The real workspace export produces a manifest and its exported Python suite passes from its own directory.

## Local study panel security

- No wildcard CORS header.
- Only loopback Host values and same-origin requests are accepted.
- State-changing requests require `application/json`.
- Security headers include CSP, no-sniff, no-referrer, no-store, and frame denial.
- The MathJax configuration is an external same-origin script; inline script execution remains disallowed.
- Rendered Markdown HTML is sanitized with an allowlist.
- Explicitly disabled external-source policy blocks CLI web search/fetch before network use and blocks external-source persistence in the kernel.
- Configured academic source roots replace hardcoded Blackboard paths.
- Course cards open an exact `index.md` when present.

## UI continuity

- Active/paused/blocked sessions appear on the initial real-data surface.
- A persisted session can be opened directly by URL after reload.
- Pause and resume are available in the graphical session surface.
- The Spanish `#/hoy` route resolves coherently.

## Verification commands

```bash
uv run --extra dev pytest -q -p no:cacheprovider
pnpm run check
pnpm run build
uv run --extra browser python tests/browser_smoke_session.py
uv build
```

Final verification: 236 Python tests pass; TypeScript check/build passes; browser continuity/security smoke passes in both the working tree and a clean extracted export; changed Python files pass Ruff. Independent review found and drove fixes for symlink escape, malformed privacy, DOM injection, stale/concurrent revisions, unexpected deletions, binary leakage, export cleanup, source-root contradictions and stale UI projections. The final UTF-8-decodable binary probe is covered by a dedicated regression test.

## Deliberately remaining after P0

- Full solo-session experience and source/rubric reveal flow.
- AI tutor provider, progressive hints, feedback validation, and source-linked correction.
- Evidence tied to session/attempt/actor/harness.
- Review completion and delayed-retrieval UX.
- Complete MCP lifecycle and cross-harness handoff contract.
- TypeScript strict migration and removal of global `@ts-nocheck`.
- Supported packaged UI/MCP launchers in the wheel.
- Network-level SSRF/redirect hardening for explicitly authorized external fetches.
- Evidence retention, redaction, deletion and optional encryption policies.
