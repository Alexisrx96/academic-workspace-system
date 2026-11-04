from __future__ import annotations

import argparse
import atexit
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from .application import AcademicWorkspaceKernel
from .browser_source import BrowserApiCollector
from .canva_discovery import _urls, discover_canva_presentations
from .canva_import import fetch_canva_url, import_canva_file, import_canva_html
from .confirmation import confirm_file_preview
from .differential import _load_source_map, check_differential
from .empty_source_state import apply_empty_source_policy
from .execution_guard import create_backup, rollback_backup, verify_execution
from .execution_summary import build_execution_summary, write_execution_summary
from .file_preview import build_file_preview
from .generation_report import capture_generation_baseline, write_generation_report
from .live_browser import (
    BlackboardSessionError,
    LiveBrowserTransport,
    launch_controlled_browser,
)
from .math_validation import validate_phs_result
from .next_study_action import next_study_action
from .phs_formalization import formalize_phs
from .phs_incidents import build_phs_incident, prepare_phs_issue, write_phs_incident
from .providers import BlackboardUltraProvider, available_providers, get_provider
from .render import _course_key, refresh_manifest, render_snapshot
from .search_index import rebuild_search_index
from .source_config import load_source_configs
from .source_validation import build_claim_evidence, classify_validation
from .spaced_review import schedule_review
from .study_metrics import build_study_metrics
from .study_preflight import build_preflight
from .study_sessions import create_attempt
from .sync_logging import SyncLogger
from .web_retrieval import fetch_external_source, search_web
from .workspace_commands import (
    init_workspace,
    load_workspace_config,
)


def _default_profile() -> Path | None:
    """Keep explicit profile support while allowing automatic discovery."""
    configured = os.environ.get("ACADEMIC_WORKSPACE_BROWSER_PROFILE")
    return Path(configured) if configured else None


def _write_execution_verification(target: Path, preview: list[dict[str, object]]) -> dict[str, object]:
    result = verify_execution(target, preview)
    path = target / ".blackboard-sync/execution-verification.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def _canva_command(argv: list[str]) -> int | None:
    if not argv or argv[0] != "canva":
        return None
    if len(argv) < 2 or argv[1] != "import":
        print("Uso: academic-workspace canva import --target TARGET (--url URL | --html FILE)", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="academic-workspace canva import")
    parser.add_argument("--target", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--html", type=Path)
    parser.add_argument("--source-url", help="URL Canva de origen cuando se importa un HTML local")
    parser.add_argument("--profile", type=Path, default=_default_profile())
    parser.add_argument("--course", action="append", default=[])
    parser.add_argument("--topic", action="append", default=[])
    parser.add_argument("--accessed-at", default=datetime.now(UTC).isoformat())
    parser.add_argument("--license", dest="license_name", default="shared-canva-content; verify permissions")
    args = parser.parse_args(argv[2:])
    try:
        if args.url:
            html = fetch_canva_url(args.url, args.profile)
            result = import_canva_html(
                html,
                args.target,
                source_url=args.url,
                accessed_at=args.accessed_at,
                related_courses=args.course,
                related_topics=args.topic,
                license_name=args.license_name,
            )
        else:
            source_url = args.source_url
            if not source_url:
                raise ValueError("--source-url es obligatorio al importar un HTML local.")
            result = import_canva_file(
                args.html,
                args.target,
                source_url=source_url,
                accessed_at=args.accessed_at,
                related_courses=args.course,
                related_topics=args.topic,
                license_name=args.license_name,
            )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    rebuild_search_index(args.target)
    print(json.dumps({
        "schema": "canva-import.v1",
        "note": result.note.relative_to(args.target).as_posix(),
        "original": result.original.relative_to(args.target).as_posix(),
        "content_hash": result.content_hash,
    }, ensure_ascii=False, indent=2))
    return 0


def _workspace_command(argv: list[str]) -> int | None:
    if not argv or argv[0] not in {"init", "doctor", "status", "report", "rollback", "study", "config", "phs"}:
        return None
    command = argv[0]
    if command == "phs":
        subcommand = argv[1] if len(argv) > 1 else "check"
        parser = argparse.ArgumentParser(prog=f"academic-workspace phs {subcommand}")
        parser.add_argument("--target", type=Path, required=True)
        if subcommand == "suggest":
            parser.add_argument("problem_or_topic")
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).recommend_phs(args.problem_or_topic)
        elif subcommand == "check":
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).phs_status()
        elif subcommand == "run":
            parser.add_argument("script")
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).run_phs(args.script)
        elif subcommand == "transpile":
            parser.add_argument("script")
            parser.add_argument("--language", default="python", choices=("python", "rust", "java"))
            parser.add_argument("--output")
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).transpile_phs(args.script, language=args.language, output=args.output)
        else:
            print("Uso: academic-workspace phs {suggest|check|run|transpile}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if subcommand == "suggest" or result.get("verified", result.get("installed", False)) else 1
    if command == "study":
        subcommand = argv[1] if len(argv) > 1 else "policy"
        parser = argparse.ArgumentParser(prog=f"academic-workspace study {subcommand}")
        parser.add_argument("--target", type=Path, required=True)
        if subcommand == "start":
            parser.add_argument("--course", required=True)
            parser.add_argument("--topic", required=True)
            parser.add_argument("--objective", required=True)
            parser.add_argument("--mode", default="guided", choices=("guided", "explicit_validation", "manual_verification", "adversarial_source"))
            parser.add_argument("--source-ref", action="append", default=[])
            parser.add_argument("--minutes", type=int, default=25)
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).start_study_session(args.course, args.topic, args.objective, args.mode, tuple(args.source_ref), args.minutes).to_dict()
        elif subcommand == "attempt":
            parser.add_argument("--session-id", required=True)
            parser.add_argument("--phase", required=True)
            parser.add_argument("--response", required=True)
            parser.add_argument("--feedback", default="")
            parser.add_argument("--result", required=True)
            parser.add_argument("--confidence", type=int)
            parser.add_argument("--help-level", type=int, default=0)
            parser.add_argument("--error-tag", action="append", default=[])
            args = parser.parse_args(argv[2:])
            kernel = AcademicWorkspaceKernel(args.target)
            session = kernel.study_session(args.session_id)
            attempt = create_attempt(session, args.phase, args.response, args.feedback, args.result, tuple(args.error_tag), confidence=args.confidence, help_level=args.help_level)
            event_id = kernel.record_study_attempt(attempt)
            review = schedule_review(args.result, args.confidence)
            review["session_id"] = args.session_id
            review["attempt_id"] = attempt.attempt_id
            review_event_id = kernel.record_study_review(review)
            result = {**attempt.to_dict(), "event_id": event_id, "next_action": next_study_action(args.result, tuple(args.error_tag), args.confidence), "review": {**review, "event_id": review_event_id}}
        elif subcommand == "status":
            parser.add_argument("--session-id", required=True)
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).study_session(args.session_id).to_dict()
        elif subcommand == "list":
            parser.add_argument("--status")
            args = parser.parse_args(argv[2:])
            sessions = AcademicWorkspaceKernel(args.target).study_sessions(status=args.status)
            result = {"schema": "study-session-list.v1", "sessions": [session.to_dict() for session in sessions]}
        elif subcommand == "preflight":
            parser.add_argument("--session-id", required=True)
            args = parser.parse_args(argv[2:])
            session = AcademicWorkspaceKernel(args.target).study_session(args.session_id).to_dict()
            result = build_preflight(args.target, session)
        elif subcommand == "ai-context":
            parser.add_argument("--session-id", required=True)
            args = parser.parse_args(argv[2:])
            kernel = AcademicWorkspaceKernel(args.target)
            session = kernel.study_session(args.session_id).to_dict()
            result = kernel.ai_study_context(session)
        elif subcommand == "metrics":
            args = parser.parse_args(argv[2:])
            result = build_study_metrics(args.target)
        elif subcommand in {"pause", "resume", "complete", "abandon"}:
            parser.add_argument("--session-id", required=True)
            args = parser.parse_args(argv[2:])
            transition = "active" if subcommand == "resume" else ("completed" if subcommand == "complete" else subcommand)
            result = AcademicWorkspaceKernel(args.target).transition_study_session(args.session_id, transition).to_dict()
        elif subcommand == "policy":
            args = parser.parse_args(argv[2:])
            result = AcademicWorkspaceKernel(args.target).study_policy()
        elif subcommand == "search":
            parser.add_argument("--query", required=True)
            parser.add_argument("--authorized", action="store_true")
            args = parser.parse_args(argv[2:])
            if not load_workspace_config(args.target).privacy.allow_external_sources:
                print("La política del workspace no permite fuentes externas.", file=sys.stderr)
                return 1
            result = {"schema": "web-search-results.v1", "query": args.query, "hits": search_web(args.query, authorized=args.authorized)}
        elif subcommand == "fetch-url":
            parser.add_argument("--url", required=True)
            parser.add_argument("--purpose", required=True)
            parser.add_argument("--authorized", action="store_true")
            parser.add_argument("--retrieved-at")
            parser.add_argument("--quote", action="append", default=[])
            args = parser.parse_args(argv[2:])
            if not load_workspace_config(args.target).privacy.allow_external_sources:
                print("La política del workspace no permite fuentes externas.", file=sys.stderr)
                return 1
            source = fetch_external_source(
                args.url,
                purpose=args.purpose,
                authorized=args.authorized,
                retrieved_at=args.retrieved_at,
                quotes=tuple(args.quote),
                artifact_root=args.target,
            )
            event_id = AcademicWorkspaceKernel(args.target).record_external_source(source)
            result = {**source.to_dict(), "event_id": event_id}
        elif subcommand == "claim":
            parser.add_argument("--source-id", required=True)
            parser.add_argument("--claim", required=True)
            parser.add_argument("--quote", required=True)
            parser.add_argument("--verdict", required=True)
            parser.add_argument("--session-id", default="")
            args = parser.parse_args(argv[2:])
            kernel = AcademicWorkspaceKernel(args.target)
            source = kernel.external_source(args.source_id)
            record = build_claim_evidence(args.claim, source, args.quote, args.verdict, args.session_id)
            record["event_id"] = kernel.record_claim_evidence(record)
            result = record
        elif subcommand == "incident":
            parser.add_argument("--course", required=True)
            parser.add_argument("--topic", required=True)
            parser.add_argument("--validation-json", type=Path, required=True)
            parser.add_argument("--checks-json", type=Path, required=True)
            args = parser.parse_args(argv[2:])
            validation = json.loads(args.validation_json.read_text(encoding="utf-8"))
            checks = json.loads(args.checks_json.read_text(encoding="utf-8"))
            report = build_phs_incident(args.course, args.topic, validation, checks)
            paths = write_phs_incident(args.target, report)
            result = {**report, "json_path": paths["json"].relative_to(args.target).as_posix(), "markdown_path": paths["markdown"].relative_to(args.target).as_posix()}
        elif subcommand == "issue-draft":
            parser.add_argument("--incident-json", type=Path, required=True)
            args = parser.parse_args(argv[2:])
            result = prepare_phs_issue(json.loads(args.incident_json.read_text(encoding="utf-8")))
        elif subcommand == "math-formalize":
            parser.add_argument("--course", required=True)
            parser.add_argument("--topic", required=True)
            parser.add_argument("--source-ref", required=True)
            parser.add_argument("--script-file", type=Path, required=True)
            parser.add_argument("--approved", action="store_true")
            args = parser.parse_args(argv[2:])
            script_text = args.script_file.read_text(encoding="utf-8")
            result = formalize_phs(
                args.target,
                course=args.course,
                topic=args.topic,
                script_text=script_text,
                source_ref=args.source_ref,
                approved=args.approved,
            )
        elif subcommand == "validate-math":
            parser.add_argument("--script", required=True)
            parser.add_argument("--student-value", required=True)
            parser.add_argument("--units", default="")
            parser.add_argument("--predicted-value")
            parser.add_argument("--predicted-units", default="")
            parser.add_argument("--topic", default="")
            args = parser.parse_args(argv[2:])
            kernel = AcademicWorkspaceKernel(args.target)
            result = validate_phs_result(
                args.script,
                student_value=args.student_value,
                student_units=args.units,
                predicted_value=args.predicted_value,
                predicted_units=args.predicted_units,
                runner=lambda script: kernel.run_phs(script),
            )
            result["phs_recommendation"] = kernel.recommend_phs(args.topic or args.script)
        elif subcommand == "validate":
            parser.add_argument("--course-claim", required=True)
            parser.add_argument("--external-claim", required=True)
            parser.add_argument("--relationship", choices=("consistent", "simplification", "ambiguous", "conflict"))
            parser.add_argument("--external-evidence", action="store_true")
            args = parser.parse_args(argv[2:])
            result = classify_validation(
                args.course_claim,
                args.external_claim,
                relationship=args.relationship,
                external_evidence=args.external_evidence,
            )
        else:
            print("Uso: academic-workspace study {start|list|attempt|status|preflight|ai-context|metrics|pause|resume|complete|abandon|policy|search|fetch-url|claim|incident|issue-draft|math-formalize|validate-math|validate}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if command == "rollback":
        parser = argparse.ArgumentParser(prog="academic-workspace rollback")
        parser.add_argument("--target", type=Path, required=True)
        parser.add_argument("--backup", type=Path)
        args = parser.parse_args(argv[1:])
        rollback_backup(args.target, args.backup)
        print(json.dumps({"schema": "rollback.v1", "status": "restored", "target": args.target.as_posix()}, ensure_ascii=False, sort_keys=True))
        return 0
    if command == "config" and len(argv) > 1 and argv[1] == "validate":
        command = "config validate"
    elif command == "config":
        print("Uso: academic-workspace config validate", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog=f"academic-workspace {command}")
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args(argv[2:] if command == "config validate" else argv[1:])
    if command == "init":
        result = init_workspace(args.target)
    elif command == "doctor":
        result = AcademicWorkspaceKernel(args.target).doctor()
    elif command == "status":
        result = AcademicWorkspaceKernel(args.target).status()
    elif command == "report":
        result = build_execution_summary(args.target)
    else:
        result = AcademicWorkspaceKernel(args.target).validate_config()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok", result.get("valid", result.get("status") != "blocked")) else 1


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    canva_result = _canva_command(raw_argv)
    if canva_result is not None:
        return canva_result
    command_result = _workspace_command(raw_argv)
    if command_result is not None:
        return command_result
    parser = argparse.ArgumentParser(description="Sincronización determinista de una fuente académica -> Obsidian")
    parser.add_argument("--target", type=Path, required=True, help="Raíz de la bóveda Obsidian")
    parser.add_argument("--provider", choices=available_providers(), default=None, help="Proveedor de fuente académica")
    parser.add_argument("--instance", default=None, help="Identidad de la instancia del proveedor")
    parser.add_argument("--source-root", default=None, help="Lane local de la fuente; se toma de sources.json si se omite")
    parser.add_argument("--profile", type=Path, default=_default_profile(), help="Perfil Chrome con sesión Blackboard ya iniciada")
    parser.add_argument("--dry-run", action="store_true", help="Construye y muestra el mapa diferencial sin escribir")
    parser.add_argument("--plan", action="store_true", help="Alias explícito de --dry-run")
    parser.add_argument("--force-sync", action="store_true", help="Vuelve a verificar fuentes marcadas como vacías y reactiva las que tengan contenido")
    parser.add_argument("--launch-browser", action="store_true", help="Lanza un Chrome controlado si no se encuentra una sesión DevTools")
    parser.add_argument("--yes", action="store_true", help="Aprueba automáticamente cambios destructivos mostrados por la vista previa")
    parser.add_argument("--no-auto-canva", action="store_true", help="No descubrir automáticamente enlaces Canva durante la sincronización")
    args = parser.parse_args(argv)
    sync_log = SyncLogger(args.target)
    sync_log.__enter__()
    atexit.register(sync_log.__exit__, None, None, None)
    sync_log.event("phase_started", phase="configuration")
    configured = load_source_configs(args.target)
    source = configured[0]
    provider_name = args.provider or source.provider
    instance = args.instance or source.instance
    source_root = args.source_root or source.root
    sync_log.event("phase_finished", phase="configuration", provider=provider_name, instance=instance, source_root=source_root)
    if provider_name != "blackboard_ultra":
        parser.error(f"El proveedor {provider_name!r} aún no tiene transporte live configurado; usa el proveedor fixture desde Python.")

    try:
        sync_log.event("phase_started", phase="browser_connect", profile_configured=bool(args.profile))
        with LiveBrowserTransport(args.profile) as transport:
            sync_log.event("phase_finished", phase="browser_connect")
            sync_log.event("phase_started", phase="collect")
            provider_factory = get_provider(provider_name)
            provider = provider_factory(
                lambda: BrowserApiCollector(transport).collect(),
                instance=instance,
            )
            if not isinstance(provider, BlackboardUltraProvider):
                parser.error("El proveedor seleccionado no es compatible con el transporte live actual.")
            snapshot = provider.collect_legacy_snapshot()
            sync_log.event("phase_finished", phase="collect", courses=len(snapshot.courses), elements=len(snapshot.activities))
            empty_policy = apply_empty_source_policy(
                snapshot,
                args.target,
                provider=provider_name,
                instance=instance,
                force=args.force_sync,
            )
            snapshot = empty_policy.snapshot
            courses_by_id = {course.id: course for course in snapshot.courses}
            canva_observations = []
            for activity in snapshot.activities:
                if not activity.body or not _urls(activity.body):
                    continue
                course = courses_by_id.get(activity.course_id)
                if course is None:
                    continue
                course_path = _course_key(course)
                source = args.target / source_root / course_path / "index.md"
                metadata = {
                    "source_course_id": course.id,
                    "source_item_id": activity.id,
                    "course_code": course.course_id or course_path,
                    "source_ref": f"{source_root}/{course_path}/{activity.title}--{activity.id}.md",
                }
                canva_observations.append((activity.body, source, metadata))
            check = check_differential(
                snapshot,
                args.target,
                source_root=source_root,
                source_provider=provider_name,
                source_instance=instance,
            )
            sync_log.event("phase_finished", phase="differential", **check.diff, downloads_required=not check.no_download_needed, integrity_ok=check.integrity_ok)
            previous_map = _load_source_map(args.target / ".blackboard-sync/source-map.json")
            file_preview = build_file_preview(check.source_map, previous_map, args.target)
            if args.dry_run or args.plan:
                print(json.dumps({
                    "courses": len(snapshot.courses),
                    "elements": len(snapshot.activities),
                    "diff": check.diff,
                    "file_preview": file_preview,
                    "integrity_ok": check.integrity_ok,
                    "downloads_required": not check.no_download_needed,
                    "empty_marked": empty_policy.marked,
                    "empty_skipped": empty_policy.skipped,
                    "empty_reactivated": empty_policy.reactivated,
                    "force_sync": args.force_sync,
                    "snapshot_sha256": check.source_map.snapshot_sha256,
                }, ensure_ascii=False, sort_keys=True))
                return 0
            if not confirm_file_preview(file_preview, approve=args.yes):
                print("Sin cambios aplicados: confirmación cancelada.", file=sys.stderr)
                return 3
            planned_paths = [path for group in file_preview for path in group.get("paths", [])]
            generation_baseline = capture_generation_baseline(args.target)
            sync_log.event(
                "baseline_captured",
                phase="backup",
                baseline_files=len(generation_baseline.get("files", {})),
                planned_paths=len(planned_paths),
                diff_added=check.diff.get("added", 0),
                diff_changed=check.diff.get("changed", 0),
            )
            create_backup(args.target, planned_paths)
            sync_log.event("phase_finished", phase="backup", planned_paths=len(planned_paths))
            if check.no_download_needed:
                if not args.no_auto_canva:
                    canva = discover_canva_presentations(
                        args.target,
                        source_root=source_root,
                        fetcher=getattr(transport, "fetch_rendered_html", lambda url: fetch_canva_url(url, args.profile)),
                        extra_observations=tuple(canva_observations),
                        on_progress=lambda phase, current, total, item: sync_log.progress(phase, current=current, total=total, item=item, scope="canva", unit="presentation"),
                    )
                    if canva.imported:
                        rebuild_search_index(args.target)
                    print(
                        f"Canva automático: descubiertos={canva.discovered}, "
                        f"importados={len(canva.imported)}, omitidos={canva.skipped}, "
                        f"errores={len(canva.failed)}"
                    )
                    for failure in canva.failed:
                        print(f"  Canva pendiente: {failure['url']} ({failure['error']})", file=sys.stderr)
                refresh_manifest(args.target, source_root=source_root)
                sync_log.event("phase_started", phase="verification")
                write_generation_report(args.target, previous=generation_baseline)
                verification = _write_execution_verification(args.target, file_preview)
                sync_log.event("phase_finished", phase="verification", status=verification.get("status"))
                write_execution_summary(args.target)
                if verification["status"] == "blocked":
                    sync_log.set_status("blocked")
                    print("ERROR: verificación posterior bloqueada.", file=sys.stderr)
                    return 4
                print(
                    f"OK diferencial: {len(snapshot.courses)} materias, {len(snapshot.activities)} elementos, "
                    "sin cambios y sin descargas."
                )
                return 0
            result = render_snapshot(
                snapshot,
                args.target,
                downloader=transport,
                control_files={".blackboard-sync/source-map.json": check.source_map.content},
                source_root=source_root,
                source_provider=provider_name,
                source_instance=instance,
                on_progress=lambda phase, current, total, item: sync_log.progress(phase, current=current, total=total, item=item, scope="snapshot", unit="activity"),
            )
            sync_log.event("phase_finished", phase="render", changed=result.changed, written=len(result.written), snapshot_activities=len(snapshot.activities), diff_items=check.diff.get("added", 0) + check.diff.get("changed", 0))
            if not args.no_auto_canva:
                canva = discover_canva_presentations(
                    args.target,
                    source_root=source_root,
                    fetcher=getattr(transport, "fetch_rendered_html", lambda url: fetch_canva_url(url, args.profile)),
                    extra_observations=tuple(canva_observations),
                    on_progress=lambda phase, current, total, item: sync_log.progress(phase, current=current, total=total, item=item, scope="canva", unit="presentation"),
                )
                if canva.imported:
                    rebuild_search_index(args.target)
                print(
                    f"Canva automático: descubiertos={canva.discovered}, "
                    f"importados={len(canva.imported)}, omitidos={canva.skipped}, "
                    f"errores={len(canva.failed)}"
                )
                for failure in canva.failed:
                    print(f"  Canva pendiente: {failure['url']} ({failure['error']})", file=sys.stderr)
            refresh_manifest(args.target, source_root=source_root)
    except BlackboardSessionError as error:
        sync_log.set_status("failed")
        if args.launch_browser:
            try:
                profile = launch_controlled_browser(args.profile)
            except BlackboardSessionError as launch_error:
                print(f"ERROR: {launch_error}", file=sys.stderr)
                return 2
            print(
                "No había una sesión DevTools disponible. Se lanzó un Chrome controlado en "
                f"{profile}. Inicia sesión manualmente en Blackboard y vuelve a ejecutar el comando."
            )
            return 3
        print(f"ERROR: {error}", file=sys.stderr)
        print("Puedes volver a ejecutar con --launch-browser para abrir un perfil controlado.", file=sys.stderr)
        return 2

    sync_log.event("phase_started", phase="verification")
    write_generation_report(args.target, previous=generation_baseline)
    verification = _write_execution_verification(args.target, file_preview)
    sync_log.event("phase_finished", phase="verification", status=verification.get("status"))
    write_execution_summary(args.target)
    if verification["status"] == "blocked":
        sync_log.set_status("blocked")
        print("ERROR: verificación posterior bloqueada; backup disponible para rollback.", file=sys.stderr)
        return 4
    action = "actualizados" if result.changed else "sin cambios"
    print(
        f"OK: {len(snapshot.courses)} materias, {len(snapshot.activities)} elementos, {action}; "
        f"vacíos nuevos={empty_policy.marked}, omitidos={empty_policy.skipped}, "
        f"reactivados={empty_policy.reactivated}; manifest={result.manifest_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
