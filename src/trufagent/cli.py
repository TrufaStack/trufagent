from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shlex
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import ValidationError

from trufagent.application.close_v2 import CloseV2Service
from trufagent.application.evaluation import evaluate_suite, load_evaluation_suite
from trufagent.application.memory_review import MemoryReviewService
from trufagent.application.memory_v2 import MemoryV2Service
from trufagent.application.plan_task import PlanTaskRequest, PlanTaskService
from trufagent.application.prepare_task import PrepareTaskRequest, PrepareTaskService
from trufagent.application.prepare_v2 import project_prepare_v2
from trufagent.application.sessions import (
    EndSessionRequest,
    EndSessionService,
    StartSessionRequest,
    StartSessionService,
)
from trufagent.application.skill_catalog import InMemorySkillCatalog
from trufagent.application.skill_import import plan_skill_import
from trufagent.application.skill_sanitization import (
    apply_skill_sanitization,
    plan_skill_sanitization,
)
from trufagent.application.task_classifier import classify_task
from trufagent.application.task_extractor import TaskIntake, extract_task_signals
from trufagent.domain.close_v2 import CloseV2Request
from trufagent.domain.memory import MemoryReviewMetadata, memory_json_schema
from trufagent.domain.skill_audit import SkillAuditReport
from trufagent.domain.skill_sanitization import SkillSanitizationManifest
from trufagent.domain.skill_sources import RemoteSkillRegistry
from trufagent.domain.task import ModelRouting, ModelTier, TaskKind, TaskSignals
from trufagent.domain.task_preview import TaskPreviewRecord
from trufagent.infrastructure.codex_skill_surface import (
    apply_managed_skill_surface,
    plan_codex_skill_surface,
)
from trufagent.infrastructure.git_merge import GitMergeVerifier
from trufagent.infrastructure.graphify_adapter import GraphifyAdapter, GraphifyAdapterError
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository, MemoryVaultError
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_markdown import (
    MemoryFormatError,
    load_memory_markdown,
    load_memory_markdown_compatible,
)
from trufagent.infrastructure.memory_v2_fs import MarkdownMemoryRepositoryV2
from trufagent.infrastructure.model_profiles import Harness, resolve_project_model
from trufagent.infrastructure.pilot_fs import (
    PilotLedgerError,
    PilotTaskKind,
    PilotTaskStatus,
    begin_pilot_task,
    finish_pilot_task,
)
from trufagent.infrastructure.project_init import ProjectInitializationError, initialize_project
from trufagent.infrastructure.session_fs import FileSessionRepository
from trufagent.infrastructure.skill_audit import audit_skill_catalog
from trufagent.infrastructure.skill_catalog_fs import SkillCatalogRepository
from trufagent.infrastructure.skill_discovery import SkillDiscovery, default_skill_roots
from trufagent.infrastructure.skill_report_fs import save_json_document
from trufagent.infrastructure.skill_sources_github import sync_pilot_sources
from trufagent.infrastructure.task_preview_fs import (
    FileTaskPreviewRepository,
    TaskPreviewError,
)
from trufagent.infrastructure.worktree_fingerprint import fingerprint_worktree

# Lazy injection point retained for the historical experimental shadow tests.
CodexShadowRunner = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trufagent")
    subcommands = parser.add_subparsers(dest="command", required=True)

    schema = subcommands.add_parser("schema", help="Print a canonical JSON Schema")
    schema.add_argument("kind", choices=["memory"])

    personal_task = subcommands.add_parser(
        "task", help="Prepare a personal task from one natural-language request"
    )
    personal_task.add_argument("task")
    personal_task.add_argument("--root", type=Path, default=Path.cwd())
    personal_task.add_argument("--project")
    personal_task.add_argument("--kind", choices=[item.value for item in TaskKind])
    personal_task.add_argument("--cause-known", action=argparse.BooleanOptionalAction, default=None)
    personal_task.add_argument(
        "--solution-known", action=argparse.BooleanOptionalAction, default=None
    )
    personal_task.add_argument(
        "--approved-plan", action=argparse.BooleanOptionalAction, default=None
    )
    personal_task.add_argument(
        "--open-decisions", action=argparse.BooleanOptionalAction, default=None
    )
    personal_task.add_argument("--localized", action=argparse.BooleanOptionalAction, default=None)
    personal_task.add_argument("--required-symbol", action="append", default=[])
    personal_task.add_argument("--use-skill", action="append", default=[])
    personal_task.add_argument("--without-skill", action="append", default=[])
    personal_task.add_argument("--include-user-memory", action="store_true")
    prepare_v2 = subcommands.add_parser(
        "prepare", help="Prepare a task using the compact Trufagent v2 contract"
    )
    prepare_v2.add_argument("intake", type=Path)
    prepare_v2.add_argument("project_root", type=Path)
    prepare_v2.add_argument("--project")
    prepare_v2.add_argument("--catalog", type=Path)
    prepare_v2.add_argument("--harness", choices=[item.value for item in Harness])
    close_v2 = subcommands.add_parser("close", help="Close a confirmed merged change")
    close_v2.add_argument("request", type=Path)
    close_v2.add_argument("project_root", type=Path)
    close_v2.add_argument("--project")
    continue_task = subcommands.add_parser(
        "task-continue", help="Continue a safe task preview explicitly"
    )
    continue_task.add_argument("preview_id")
    continue_task.add_argument("--root", type=Path, default=Path.cwd())
    continue_task.add_argument("--mode", choices=["local", "shadow"], required=True)
    continue_task.add_argument("--task-text")
    continue_task.add_argument("--confirm", action="store_true")

    memory = subcommands.add_parser("memory", help="Memory operations")
    memory_subcommands = memory.add_subparsers(dest="memory_command", required=True)
    validate = memory_subcommands.add_parser("validate", help="Validate a memory document")
    validate.add_argument("path", type=Path)
    memory_list = memory_subcommands.add_parser("list", help="List effective memories")
    memory_list.add_argument("project_root", type=Path)
    memory_list.add_argument("--project", required=True)
    memory_list.add_argument("--status")
    show_memory = memory_subcommands.add_parser("show", help="Show effective memory")
    show_memory.add_argument("project_root", type=Path)
    show_memory.add_argument("memory_id")
    show_memory.add_argument("--project", required=True)
    history_memory = memory_subcommands.add_parser("history", help="Show review history")
    history_memory.add_argument("project_root", type=Path)
    history_memory.add_argument("memory_id")
    history_memory.add_argument("--project", required=True)
    accept_memory = memory_subcommands.add_parser("accept", help="Accept proposed memory")
    accept_memory.add_argument("project_root", type=Path)
    accept_memory.add_argument("memory_id")
    accept_memory.add_argument("--project", required=True)
    accept_memory.add_argument("--reviewer", required=True)
    accept_memory.add_argument("--metadata", type=Path)
    propose_memory = memory_subcommands.add_parser(
        "propose", help="Create a canonical proposed memory"
    )
    propose_memory.add_argument("project_root", type=Path)
    propose_memory.add_argument("document", type=Path)
    propose_memory.add_argument("--project", required=True)
    reject_memory = memory_subcommands.add_parser("reject", help="Reject proposed memory")
    reject_memory.add_argument("project_root", type=Path)
    reject_memory.add_argument("memory_id")
    reject_memory.add_argument("--project", required=True)
    reject_memory.add_argument("--reviewer", required=True)
    reject_memory.add_argument("--reason", required=True)
    supersede_memory = memory_subcommands.add_parser("supersede", help="Supersede accepted memory")
    supersede_memory.add_argument("project_root", type=Path)
    supersede_memory.add_argument("memory_id")
    supersede_memory.add_argument("--with", dest="replacement_id", required=True)
    supersede_memory.add_argument("--project", required=True)
    supersede_memory.add_argument("--reviewer", required=True)
    supersede_memory.add_argument("--reason", required=True)
    replace_memory = memory_subcommands.add_parser("replace", help="Replace accepted v2 memory")
    replace_memory.add_argument("project_root", type=Path)
    replace_memory.add_argument("memory_id")
    replace_memory.add_argument("--with", dest="replacement_id", required=True)
    replace_memory.add_argument("--project", required=True)
    replace_memory.add_argument("--reviewer", required=True)
    replace_memory.add_argument("--reason", required=True)
    retire_memory = memory_subcommands.add_parser("retire", help="Retire active v2 memory")
    retire_memory.add_argument("project_root", type=Path)
    retire_memory.add_argument("memory_id")
    retire_memory.add_argument("--project", required=True)
    retire_memory.add_argument("--reviewer", required=True)
    retire_memory.add_argument("--reason", required=True)

    cartography = subcommands.add_parser("cartography", help="Graphify cartography operations")
    cartography_subcommands = cartography.add_subparsers(dest="cartography_command", required=True)
    status = cartography_subcommands.add_parser("status", help="Inspect graph freshness")
    status.add_argument("project_root", type=Path)
    update = cartography_subcommands.add_parser("update", help="Update the local AST graph")
    update.add_argument("project_root", type=Path)
    query = cartography_subcommands.add_parser("query", help="Query a scoped structural graph")
    query.add_argument("project_root", type=Path)
    query.add_argument("question")
    query.add_argument("--budget", type=int, default=2_000)
    affected = cartography_subcommands.add_parser("affected", help="Find reverse impact")
    affected.add_argument("project_root", type=Path)
    affected.add_argument("label")
    affected.add_argument("--relation", action="append", default=[])
    affected.add_argument("--depth", type=int, default=2)

    plan = subcommands.add_parser("plan", help="Task strategy operations")
    plan_subcommands = plan.add_subparsers(dest="plan_command", required=True)
    classify = plan_subcommands.add_parser("classify", help="Classify typed task signals")
    classify.add_argument("signals", type=Path)
    extract = plan_subcommands.add_parser("extract", help="Extract correctable task signals")
    extract.add_argument("intake", type=Path)
    prepare = plan_subcommands.add_parser("prepare", help="Extract signals and build a task plan")
    prepare.add_argument("intake", type=Path)
    prepare.add_argument("project_root", type=Path)
    prepare.add_argument("--project")
    prepare.add_argument("--catalog", type=Path)
    task = plan_subcommands.add_parser("task", help="Build a complete task plan")
    task.add_argument("request", type=Path)
    task.add_argument("--catalog", type=Path)

    models = subcommands.add_parser("models", help="Resolve harness model profiles")
    models_subcommands = models.add_subparsers(dest="models_command", required=True)
    resolve = models_subcommands.add_parser(
        "resolve", help="Resolve a project tier to a concrete model"
    )
    resolve.add_argument("project_root", type=Path)
    resolve.add_argument("--harness", choices=[item.value for item in Harness], required=True)
    resolve.add_argument(
        "--tier",
        choices=["none", "economy", "balanced", "frontier"],
        required=True,
    )

    delegation = subcommands.add_parser(
        "delegation", help="Compile bounded delegation and record usage"
    )
    delegation_subcommands = delegation.add_subparsers(dest="delegation_command", required=True)
    compile_protocol = delegation_subcommands.add_parser(
        "compile", help="Compile a provider-specific bounded protocol"
    )
    compile_protocol.add_argument("project_root", type=Path)
    compile_protocol.add_argument("request", type=Path)
    dry_run = delegation_subcommands.add_parser(
        "dry-run", help="Execute a protocol with scripted fake handoffs"
    )
    dry_run.add_argument("protocol", type=Path)
    dry_run.add_argument("script", type=Path)
    shadow = delegation_subcommands.add_parser(
        "shadow", help="Prepare or explicitly run read-only Codex exploration"
    )
    shadow.add_argument("project_root", type=Path)
    shadow.add_argument("--session", required=True)
    shadow.add_argument("--task", required=True)
    shadow_source = shadow.add_mutually_exclusive_group(required=True)
    shadow_source.add_argument("--signals", type=Path)
    shadow_source.add_argument("--preview")
    shadow.add_argument("--required-symbol", action="append", default=[])
    shadow.add_argument(
        "--tier",
        choices=["economy", "balanced", "frontier"],
    )
    shadow.add_argument("--model")
    shadow.add_argument("--budget-limit-usd", type=Decimal, required=True)
    shadow.add_argument("--estimated-cost-usd", type=Decimal, required=True)
    shadow.add_argument("--confirm-provider", action="store_true")
    shadow.add_argument("--attempt", type=int, choices=[1, 2], default=1)
    shadow.add_argument("--confirm-retry", action="store_true")
    attempts = delegation_subcommands.add_parser(
        "attempts", help="Inspect create-only provider attempt events"
    )
    attempts.add_argument("project_root", type=Path)
    attempts.add_argument("session_id")
    usage = delegation_subcommands.add_parser("usage", help="Usage ledger operations")
    usage_subcommands = usage.add_subparsers(dest="usage_command", required=True)
    append_usage = usage_subcommands.add_parser("append", help="Append a create-only usage event")
    append_usage.add_argument("project_root", type=Path)
    append_usage.add_argument("record", type=Path)
    usage_status = usage_subcommands.add_parser("status", help="Summarize a session usage ledger")
    usage_status.add_argument("project_root", type=Path)
    usage_status.add_argument("session_id")
    usage_status.add_argument("--budget-limit-usd")

    skills = subcommands.add_parser("skills", help="Personal skill catalog")
    skills_subcommands = skills.add_subparsers(dest="skills_command", required=True)
    sync = skills_subcommands.add_parser("sync", help="Discover and sync installed skills")
    sync.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    review = skills_subcommands.add_parser("review", help="Approve a catalog entry")
    review.add_argument("entry_id")
    review.add_argument("--activate", action="store_true")
    review.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    list_skills = skills_subcommands.add_parser("list", help="List catalog entries")
    list_skills.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    search_skills = skills_subcommands.add_parser(
        "search", help="Search reviewed skills by capability"
    )
    search_skills.add_argument("query")
    search_skills.add_argument("--harness", choices=[item.value for item in Harness])
    search_skills.add_argument("--limit", type=int, default=10)
    search_skills.add_argument("--include-unreviewed", action="store_true")
    search_skills.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    audit_skills = skills_subcommands.add_parser(
        "audit", help="Statically evaluate every local catalog variant"
    )
    audit_skills.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    audit_skills.add_argument(
        "--report",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "audit.json",
    )
    sources = skills_subcommands.add_parser(
        "sources", help="Refresh the governed remote source registry"
    )
    sources.add_argument(
        "--registry",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "sources.json",
    )
    sanitize = skills_subcommands.add_parser(
        "sanitize", help="Plan a recoverable skill library sanitization"
    )
    sanitize_mode = sanitize.add_mutually_exclusive_group(required=True)
    sanitize_mode.add_argument("--plan", action="store_true")
    sanitize_mode.add_argument("--apply", type=Path, metavar="MANIFEST")
    sanitize.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    sanitize.add_argument(
        "--audit",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "audit.json",
    )
    sanitize.add_argument(
        "--manifest",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "sanitization-plan.json",
    )
    sanitize.add_argument(
        "--archive-root",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "archive" / "v1",
    )
    import_skills = skills_subcommands.add_parser(
        "import", help="Plan governed direct imports and local adaptations"
    )
    import_skills.add_argument("--plan", action="store_true", required=True)
    import_skills.add_argument("--direct", action="append", default=[])
    import_skills.add_argument("--adapt", action="append", default=[])
    import_skills.add_argument(
        "--sources",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "sources.json",
    )
    import_skills.add_argument(
        "--manifest",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "import-plan.json",
    )
    import_skills.add_argument(
        "--vendor-root",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "vendor",
    )
    import_skills.add_argument(
        "--adaptation-root", type=Path, default=Path("skills") / "adapted"
    )
    profile = skills_subcommands.add_parser(
        "profile", help="Plan or apply a curated harness skill surface"
    )
    profile.add_argument("--platform", choices=["codex"], required=True)
    profile.add_argument("--apply", action="store_true")
    profile.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )
    profile.add_argument(
        "--skill-root",
        type=Path,
        default=Path.home() / ".codex" / "skills",
    )
    profile.add_argument(
        "--config",
        type=Path,
        default=Path.home() / ".codex" / "config.toml",
    )

    initialize = subcommands.add_parser("init", help="Initialize a Trufagent project")
    initialize.add_argument("project_root", type=Path)
    initialize.add_argument("--project", required=True)
    initialize.add_argument(
        "--catalog",
        type=Path,
        default=Path.home() / ".trufagent" / "skills" / "catalog.yaml",
    )

    promotion = subcommands.add_parser("promotion", help="Pilot promotion controls")
    promotion_subcommands = promotion.add_subparsers(
        dest="promotion_command", required=True
    )
    promotion_init = promotion_subcommands.add_parser(
        "init", help="Create the generic fail-closed pilot policy"
    )
    promotion_init.add_argument("project_root", type=Path)
    promotion_status = promotion_subcommands.add_parser(
        "status", help="Evaluate observed promotion readiness"
    )
    promotion_status.add_argument("project_root", type=Path)
    promotion_workspace = promotion_subcommands.add_parser(
        "workspace", help="Prepare a sanitized isolated write workspace"
    )
    promotion_workspace.add_argument("project_root", type=Path)
    promotion_review = promotion_subcommands.add_parser(
        "review", help="Create a sealed diff for human review"
    )
    promotion_review.add_argument("project_root", type=Path)
    promotion_approve = promotion_subcommands.add_parser(
        "approve", help="Approve exactly one sealed review without applying it"
    )
    promotion_approve.add_argument("project_root", type=Path)
    promotion_approve.add_argument("--confirm-review-id", required=True)
    promotion_pilot_begin = promotion_subcommands.add_parser(
        "pilot-begin", help="Begin one fingerprint-sealed pilot task"
    )
    promotion_pilot_begin.add_argument("project_root", type=Path)
    promotion_pilot_begin.add_argument("--task-id", required=True)
    promotion_pilot_begin.add_argument("--kind", type=PilotTaskKind, required=True)
    promotion_pilot_finish = promotion_subcommands.add_parser(
        "pilot-finish", help="Finish one pilot task and verify the source boundary"
    )
    promotion_pilot_finish.add_argument("project_root", type=Path)
    promotion_pilot_finish.add_argument("--task-id", required=True)
    promotion_pilot_finish.add_argument(
        "--status",
        type=PilotTaskStatus,
        choices=(PilotTaskStatus.PASSED, PilotTaskStatus.FAILED),
        required=True,
    )

    session = subcommands.add_parser("session", help="Session lifecycle")
    session_subcommands = session.add_subparsers(dest="session_command", required=True)
    start_session = session_subcommands.add_parser("start", help="Start or resume a session")
    start_session.add_argument("project_root", type=Path)
    start_session.add_argument("--project")
    start_session.add_argument("--objective")
    status_session = session_subcommands.add_parser("status", help="Show current session")
    status_session.add_argument("project_root", type=Path)
    end_session = session_subcommands.add_parser("end", help="Close the current session")
    end_session.add_argument("project_root", type=Path)
    end_session.add_argument("request", type=Path)
    end_session.add_argument("--project")

    evaluate = subcommands.add_parser("eval", help="Run deterministic evaluations")
    evaluate_subcommands = evaluate.add_subparsers(dest="eval_command", required=True)
    casebook = evaluate_subcommands.add_parser(
        "casebook", help="Evaluate task sizing against a casebook suite"
    )
    casebook.add_argument("suite", type=Path)
    casebook.add_argument("--fail-under", type=float, default=0)

    return parser


def _configured_catalog(project_root: Path) -> Path | None:
    config_path = project_root / ".trufagent" / "config.yaml"
    if not config_path.is_file():
        return None
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    skills = raw.get("skills")
    if not isinstance(skills, dict) or not skills.get("catalog"):
        return None
    return Path(str(skills["catalog"]))


def _configured_project(project_root: Path) -> str:
    config_path = project_root / ".trufagent" / "config.yaml"
    if not config_path.is_file():
        raise ValueError(f"project is required: pass --project or initialize {project_root}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw.get("project"):
        raise ValueError(f"project is missing from {config_path}")
    return str(raw["project"])


def _project(project_root: Path, override: str | None) -> str:
    return override or _configured_project(project_root)


def _runtime_catalog(project_root: Path, override: Path | None) -> InMemorySkillCatalog:
    catalog_path = override or _configured_catalog(project_root)
    if catalog_path is None:
        return InMemorySkillCatalog([])
    if not catalog_path.is_file():
        raise FileNotFoundError(f"configured skill catalog not found: {catalog_path}")
    return InMemorySkillCatalog.from_document(SkillCatalogRepository(catalog_path).load())


def _prepare_from_files(
    intake_path: Path,
    project_root: Path,
    *,
    project_override: str | None,
    catalog_override: Path | None,
    harness: Harness | None = None,
):
    project = _project(project_root, project_override)
    intake = TaskIntake.model_validate_json(intake_path.read_text(encoding="utf-8"))
    repository = MarkdownMemoryRepository(
        project_root,
        project=project,
        user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
    ).initialize()
    planner = PlanTaskService(
        repository,
        cartography=GraphifyAdapter(),
        skills=_runtime_catalog(project_root, catalog_override),
    )
    return PrepareTaskService(planner).prepare(
        PrepareTaskRequest(
            intake=intake,
            project=project,
            project_root=project_root,
            harness=harness,
        )
    )


def _shadow_schema_path() -> Path:
    path = Path(__file__).resolve().parent / "schemas" / "handoff-schema.json"
    if not path.is_file():
        raise FileNotFoundError(f"packaged shadow handoff schema not found: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "schema":
        print(json.dumps(memory_json_schema(), indent=2))
        return 0

    if args.command == "prepare":
        try:
            prepared = _prepare_from_files(
                args.intake,
                args.project_root,
                project_override=args.project,
                catalog_override=args.catalog,
                harness=Harness(args.harness) if args.harness else None,
            )
            result = project_prepare_v2(prepared, harness=args.harness)
        except (OSError, ValueError, ValidationError, MemoryVaultError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json(by_alias=True))
        return 0

    if args.command == "close":
        try:
            project = _project(args.project_root, args.project)
            repository = MarkdownMemoryRepository(
                args.project_root,
                project=project,
                user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
            ).initialize()
            request = CloseV2Request.model_validate_json(
                args.request.read_text(encoding="utf-8")
            )
            result = CloseV2Service(
                MarkdownMemoryRepositoryV2(
                    args.project_root, project=project
                ).initialize(),
                repository,
                SqliteMemoryIndex(
                    Path(args.project_root) / ".trufagent" / "memory-index.sqlite3"
                ),
                GitMergeVerifier(),
                GraphifyAdapter(),
                project=project,
            ).close(args.project_root, request)
        except (
            OSError,
            ValueError,
            ValidationError,
            GraphifyAdapterError,
            MemoryVaultError,
        ) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json(by_alias=True))
        return 0

    if args.command == "task-continue":
        try:
            root = args.root.resolve()
            preview = FileTaskPreviewRepository(root).read(args.preview_id)
            current = FileSessionRepository(root).current()
            if current is None or current.id != preview.session_id:
                raise ValueError("task preview does not belong to the active session")
            if args.task_text is not None:
                observed = hashlib.sha256(args.task_text.encode()).hexdigest()
                if observed != preview.task_digest:
                    raise ValueError("task text does not match the preview digest")
            if not args.confirm:
                print(
                    json.dumps(
                        {
                            "schema": "trufagent.task-continuation.v1",
                            "status": "confirmation-required",
                            "preview_id": preview.preview_id,
                            "mode": args.mode,
                            "summary": preview.summary,
                            "autonomy": preview.autonomy.value,
                            "route": preview.route.model_dump(mode="json"),
                            "next_action": "Review the preview, then rerun with --confirm.",
                        }
                    )
                )
                return 2
            if preview.autonomy.value in {"confirm", "block"}:
                raise ValueError(
                    f"preview autonomy {preview.autonomy.value} requires resolving its gate first"
                )
            if args.mode == "shadow":
                if args.task_text is None:
                    raise ValueError("shadow continuation requires --task-text")
                if preview.route.exploration == ModelTier.NONE:
                    print(
                        json.dumps(
                            {
                                "schema": "trufagent.task-continuation.v1",
                                "status": "not-needed",
                                "preview_id": preview.preview_id,
                                "mode": "shadow",
                                "summary": "Model exploration is already tier none.",
                                "next_action": "Use local continuation.",
                            }
                        )
                    )
                    return 0
                print(
                    json.dumps(
                        {
                            "schema": "trufagent.task-continuation.v1",
                            "status": "authorization-required",
                            "preview_id": preview.preview_id,
                            "mode": "shadow",
                            "signals": preview.signals.model_dump(mode="json"),
                            "required_symbols": list(preview.required_symbols),
                            "model_tier": preview.route.exploration.value,
                            "required_inputs": [
                                "verified_task_text",
                                "budget_limit_usd",
                                "estimated_cost_usd",
                                "confirm_provider",
                            ],
                            "shadow_invocation": {
                                "command": "trufagent delegation shadow",
                                "project_root": str(root),
                                "session": preview.session_id,
                                "preview": preview.preview_id,
                                "task_text": "reuse the exact verified --task-text input",
                                "inherits": [
                                    "signals",
                                    "required_symbols",
                                    "model_tier",
                                ],
                                "required_flags": [
                                    "--budget-limit-usd",
                                    "--estimated-cost-usd",
                                    "--confirm-provider",
                                ],
                            },
                            "next_action": (
                                "Authorize a budgeted read-only shadow invocation; "
                                "execution and verification remain disabled."
                            ),
                        }
                    )
                )
                return 0
            print(
                json.dumps(
                    {
                        "schema": "trufagent.local-handoff.v1",
                        "status": "ready",
                        "preview_id": preview.preview_id,
                        "mode": "local",
                        "summary": preview.summary,
                        "skills": list(preview.skills),
                        "memory": list(preview.memory_ids),
                        "structural_targets": list(preview.structural_targets),
                        "evidence_required": list(preview.evidence_required),
                        "warnings": list(preview.warnings),
                        "next_action": (
                            "The host may implement locally within this evidence contract."
                        ),
                    }
                )
            )
            return 0
        except (OSError, ValueError, ValidationError, TaskPreviewError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1

    if args.command == "eval":
        try:
            if not 0 <= args.fail_under <= 1:
                raise ValueError("--fail-under must be between 0 and 1")
            report = evaluate_suite(load_evaluation_suite(args.suite))
        except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(report.model_dump_json())
        return int(report.pass_rate < args.fail_under)

    if args.command == "models":
        try:
            result = resolve_project_model(
                args.project_root,
                Harness(args.harness),
                ModelTier(args.tier),
            )
        except (OSError, ValueError, ValidationError, yaml.YAMLError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json())
        return 0

    if args.command == "delegation":
        from trufagent.application.delegation import (
            CompileDelegationRequest,
            compile_delegation_protocol,
            compile_request,
        )
        from trufagent.application.delegation_executor import execute_dry_run
        from trufagent.application.exploration_gate import (
            ExplorationDisposition,
            evaluate_graphify_applicability,
            evaluate_graphify_first,
        )
        from trufagent.application.retry_gate import evaluate_supervised_retry
        from trufagent.domain.attempt import AttemptStatus
        from trufagent.domain.delegation import (
            ActionScope,
            DelegationPhase,
            DelegationProtocol,
            DelegationStep,
            PhaseHandoff,
            UsageRecord,
        )
        from trufagent.infrastructure.attempt_fs import (
            AttemptLedgerError,
            JsonlAttemptRepository,
        )
        from trufagent.infrastructure.codex_shadow_runner import (
            CodexShadowRunner as NativeCodexShadowRunner,
        )
        from trufagent.infrastructure.codex_shadow_runner import (
            ShadowProviderError,
        )
        from trufagent.infrastructure.fake_phase_adapter import ScriptedPhaseAdapter
        from trufagent.infrastructure.promotion_fs import load_promotion_policy
        from trufagent.infrastructure.shadow_phase_adapter import ShadowPhaseAdapter
        from trufagent.infrastructure.usage_fs import JsonlUsageRepository, UsageLedgerError

        try:
            if args.delegation_command == "compile":
                request = CompileDelegationRequest.model_validate_json(
                    args.request.read_text(encoding="utf-8")
                )
                print(compile_request(args.project_root, request).model_dump_json(by_alias=True))
                return 0
            if args.delegation_command == "dry-run":
                protocol = DelegationProtocol.model_validate_json(
                    args.protocol.read_text(encoding="utf-8")
                )
                raw_script = json.loads(args.script.read_text(encoding="utf-8"))
                if not isinstance(raw_script, dict):
                    raise ValueError("dry-run script must be a phase-to-handoff mapping")
                handoffs = {
                    DelegationPhase(phase): PhaseHandoff.model_validate(handoff)
                    for phase, handoff in raw_script.items()
                }
                report = execute_dry_run(
                    protocol,
                    ScriptedPhaseAdapter(handoffs),
                )
                print(report.model_dump_json())
                return int(report.status != "success")
            if args.delegation_command == "shadow":
                if args.preview is not None:
                    preview = FileTaskPreviewRepository(args.project_root).read(args.preview)
                    current = FileSessionRepository(args.project_root).current()
                    if current is None or current.id != args.session:
                        raise ValueError(
                            "shadow preview requires its active session"
                        )
                    if preview.session_id != args.session:
                        raise ValueError("shadow preview does not belong to the requested session")
                    if preview.worktree_fingerprint is None:
                        raise ValueError(
                            "shadow preview has no worktree seal; regenerate the preview"
                        )
                    if fingerprint_worktree(args.project_root) != preview.worktree_fingerprint:
                        raise ValueError(
                            "worktree changed since preview; regenerate before "
                            "provider authorization"
                        )
                    if hashlib.sha256(args.task.encode()).hexdigest() != preview.task_digest:
                        raise ValueError("task text does not match the shadow preview digest")
                    if args.required_symbol:
                        raise ValueError(
                            "--required-symbol cannot override a shadow preview"
                        )
                    if args.tier is not None:
                        raise ValueError("--tier cannot override a shadow preview")
                    signals = preview.signals
                    required_symbols = list(preview.required_symbols)
                    structural_targets = list(preview.structural_targets)
                    memory_ids = tuple(preview.memory_ids)
                    preview_id = preview.preview_id
                    graph_state = preview.graph_state
                    graph_commit = preview.graph_commit
                    graphify_version = preview.graphify_version
                    session_active = True
                    preview_fresh = True
                    exploration_tier = preview.route.exploration
                    if exploration_tier == ModelTier.NONE:
                        raise ValueError("shadow preview has exploration tier none")
                else:
                    signals = TaskSignals.model_validate_json(
                        args.signals.read_text(encoding="utf-8")
                    )
                    required_symbols = args.required_symbol
                    structural_targets = []
                    memory_ids = ()
                    preview_id = None
                    graph_state = None
                    graph_commit = None
                    graphify_version = None
                    session_active = None
                    preview_fresh = None
                    exploration_tier = ModelTier(args.tier or "balanced")
                task_payload = json.dumps(
                    {
                        "task": args.task,
                        "signals": signals.model_dump(mode="json"),
                        "required_symbols": sorted(required_symbols),
                    },
                    sort_keys=True,
                )
                task_digest = hashlib.sha256(task_payload.encode()).hexdigest()
                applicability = evaluate_graphify_applicability(
                    signals=signals,
                    required_symbols=required_symbols,
                )
                graph_queries = 0
                gate = None
                graph = None
                if applicability.should_query:
                    graph = GraphifyAdapter().query(
                        args.project_root,
                        args.task,
                        token_budget=12_000,
                    )
                    graph_queries = 1
                    gate = evaluate_graphify_first(
                        signals=signals,
                        graph=graph,
                        required_symbols=required_symbols,
                    )
                    graph_state = graph.graph_state.value
                    graph_commit = graph.graph_commit
                    graphify_version = graph.graphify_version
                if gate is not None and gate.disposition == ExplorationDisposition.MODEL_FREE:
                    print(
                        json.dumps(
                            {
                                **gate.model_dump(mode="json"),
                                "graph_queries": graph_queries,
                                "model_invocations": 0,
                            }
                        )
                    )
                    return 0
                reasons = list(gate.reasons) if gate is not None else list(applicability.reasons)
                exploration_model = args.model or resolve_project_model(
                    args.project_root,
                    Harness.CODEX,
                    exploration_tier,
                ).model
                preflight_step = DelegationStep(
                    phase=DelegationPhase.EXPLORATION,
                    tier=exploration_tier,
                    model=exploration_model,
                    action_scope=ActionScope.READ_ONLY,
                    max_attempts=1,
                )
                shadow_runner_type = CodexShadowRunner or NativeCodexShadowRunner
                shadow_runner = shadow_runner_type(
                    project_root=args.project_root,
                    session_id=args.session,
                    task=args.task,
                    schema_path=_shadow_schema_path(),
                    required_symbols=required_symbols,
                    structural_targets=structural_targets,
                    authorized_estimate_usd=args.estimated_cost_usd,
                    context_policy=(
                        load_promotion_policy(args.project_root).context
                        if (args.project_root / ".trufagent" / "promotion.yaml").exists()
                        else None
                    ),
                )
                if not args.confirm_provider:
                    preflight = shadow_runner.preflight(
                        preflight_step,
                        budget_limit_usd=args.budget_limit_usd,
                        memory_ids=memory_ids,
                        preview_id=preview_id,
                        graph_state=graph_state,
                        graph_commit=graph_commit,
                        graphify_version=graphify_version,
                        session_active=session_active,
                        preview_fresh=preview_fresh,
                    )
                    print(
                        json.dumps(
                            {
                                "status": "warning",
                                "disposition": "shadow-required",
                                "summary": "Provider invocation requires explicit confirmation.",
                                "reasons": reasons,
                                "graph_queries": graph_queries,
                                "model_invocations": 0,
                                "preflight": preflight.model_dump(
                                    mode="json", by_alias=True
                                ),
                            }
                        )
                    )
                    return 1
                usage_repository = JsonlUsageRepository(args.project_root)
                ledger = usage_repository.load(
                    args.session,
                    budget_limit_usd=args.budget_limit_usd,
                )
                if ledger.has_unbounded_unknown_cost:
                    raise ValueError(
                        "cannot authorize provider call while prior session cost is unknown"
                    )
                ledger.authorize(args.estimated_cost_usd)
                attempt_repository = JsonlAttemptRepository(args.project_root)
                prior_events = attempt_repository.for_task(args.session, task_digest)
                started = [event for event in prior_events if event.status == AttemptStatus.STARTED]
                if args.attempt == 2:
                    failed = [
                        event for event in prior_events if event.status == AttemptStatus.FAILED
                    ]
                    if len(started) != 1 or len(failed) != 1:
                        raise ValueError(
                            "attempt 2 requires one durable started and failed attempt"
                        )
                    prior = failed[0]
                    retry = evaluate_supervised_retry(
                        failure_kind=prior.failure_kind,
                        prior_attempts=len(started),
                        worktree_unchanged=prior.worktree_unchanged is True,
                        budget_authorized=True,
                        human_confirmed=args.confirm_retry,
                    )
                    if not retry.allowed:
                        print(retry.model_dump_json())
                        return 1
                elif started:
                    raise ValueError(
                        "attempt 1 already exists for this task; inspect its durable history"
                    )
                protocol = compile_delegation_protocol(
                    session_id=args.session,
                    project_root=args.project_root,
                    harness=Harness.CODEX,
                    route=ModelRouting(
                        coordinator=ModelTier.NONE,
                        exploration=exploration_tier,
                        execution=ModelTier.NONE,
                        verification=ModelTier.NONE,
                    ),
                    evidence_required=[],
                )
                exploration = protocol.steps[1].model_copy(
                    update={"model": exploration_model}
                )
                protocol = protocol.model_copy(
                    update={
                        "budget_limit_usd": args.budget_limit_usd,
                        "steps": (
                            protocol.steps[0],
                            exploration,
                            protocol.steps[2],
                            protocol.steps[3],
                        ),
                    }
                )
                adapter = ShadowPhaseAdapter(
                    project_root=args.project_root,
                    session_id=args.session,
                    harness=Harness.CODEX,
                    runner=shadow_runner,
                    usage=usage_repository,
                    attempts=attempt_repository,
                    task_digest=task_digest,
                    attempt=args.attempt,
                )
                report = execute_dry_run(protocol, adapter)
                print(report.model_dump_json())
                return int(report.status != "success")
            if args.delegation_command == "attempts":
                events = JsonlAttemptRepository(args.project_root).load(args.session_id)
                print(
                    json.dumps(
                        {
                            "schema": "trufagent.attempt-history.v1",
                            "session_id": args.session_id,
                            "events": [
                                event.model_dump(mode="json", by_alias=True) for event in events
                            ],
                        }
                    )
                )
                return 0
            repository = JsonlUsageRepository(args.project_root)
            if args.usage_command == "append":
                record = UsageRecord.model_validate_json(args.record.read_text(encoding="utf-8"))
                path = repository.append(record)
                print(json.dumps({"status": "appended", "path": str(path)}))
                return 0
            ledger = repository.load(
                args.session_id,
                budget_limit_usd=args.budget_limit_usd,
            )
            print(
                json.dumps(
                    {
                        "session_id": ledger.session_id,
                            "records": len(ledger.records),
                            "known_cost_usd": str(ledger.known_cost_usd),
                            "reserved_cost_usd": str(ledger.reserved_cost_usd),
                            "has_unknown_cost": ledger.has_unknown_cost,
                            "has_unbounded_unknown_cost": (
                                ledger.has_unbounded_unknown_cost
                            ),
                            "cost_status": ledger.cost_status,
                            "remaining_budget_usd": (
                                str(ledger.remaining_budget_usd)
                                if ledger.remaining_budget_usd is not None
                                else None
                            ),
                        "budget_limit_usd": (
                            str(ledger.budget_limit_usd)
                            if ledger.budget_limit_usd is not None
                            else None
                        ),
                    }
                )
            )
            return 0
        except (
            OSError,
            AttemptLedgerError,
            ValueError,
            ValidationError,
            ShadowProviderError,
            UsageLedgerError,
            yaml.YAMLError,
        ) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1

    if args.command == "cartography":
        cartography = GraphifyAdapter()
        try:
            if args.cartography_command == "status":
                result = cartography.status(args.project_root)
            elif args.cartography_command == "update":
                result = cartography.update(args.project_root)
            elif args.cartography_command == "query":
                result = cartography.query(
                    args.project_root, args.question, token_budget=args.budget
                )
            else:
                result = cartography.affected(
                    args.project_root,
                    args.label,
                    relations=args.relation,
                    depth=args.depth,
                )
        except (OSError, GraphifyAdapterError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json())
        return 0

    if args.command == "plan" and args.plan_command == "classify":
        try:
            signals = TaskSignals.model_validate_json(args.signals.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(classify_task(signals).model_dump_json())
        return 0

    if args.command == "plan" and args.plan_command == "extract":
        try:
            intake = TaskIntake.model_validate_json(args.intake.read_text(encoding="utf-8"))
            result = extract_task_signals(intake)
        except (OSError, ValueError, ValidationError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json())
        return 0

    if args.command == "plan" and args.plan_command == "prepare":
        try:
            result = _prepare_from_files(
                args.intake,
                args.project_root,
                project_override=args.project,
                catalog_override=args.catalog,
            )
        except (OSError, ValueError, ValidationError, MemoryVaultError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json())
        return 0

    if args.command == "plan" and args.plan_command == "task":
        try:
            request = PlanTaskRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
            runtime_catalog = _runtime_catalog(request.project_root, args.catalog)
            repository = MarkdownMemoryRepository(
                request.project_root,
                project=request.project,
                user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
            ).initialize()
            service = PlanTaskService(
                repository,
                cartography=GraphifyAdapter(),
                skills=runtime_catalog,
            )
            result = service.plan(request)
        except (OSError, ValueError, ValidationError, MemoryVaultError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(result.model_dump_json())
        return 0

    if args.command == "skills":
        catalog_path = getattr(
            args, "catalog", Path.home() / ".trufagent" / "skills" / "catalog.yaml"
        )
        repository = SkillCatalogRepository(catalog_path)
        try:
            if args.skills_command == "sync":
                roots, metadata = default_skill_roots(Path.home())
                discovery = SkillDiscovery(roots, root_metadata=metadata).scan()
                catalog = repository.sync(discovery.catalog)
                print(
                    json.dumps(
                        {
                            "status": "success",
                            "catalog": str(args.catalog),
                            "entries": len(catalog.entries),
                            "reviewed": sum(entry.reviewed for entry in catalog.entries),
                            "conflicts": sum(not entry.active for entry in catalog.entries),
                            "warnings": discovery.warnings,
                        }
                    )
                )
            elif args.skills_command == "review":
                catalog = repository.review(args.entry_id, activate=args.activate)
                print(
                    json.dumps(
                        {
                            "status": "success",
                            "entry_id": args.entry_id,
                            "reviewed": sum(entry.reviewed for entry in catalog.entries),
                        }
                    )
                )
            elif args.skills_command == "list":
                print(repository.load().model_dump_json(by_alias=True))
            elif args.skills_command == "search":
                library = InMemorySkillCatalog.from_document(repository.load())
                matches = library.search(
                    args.query,
                    harness=args.harness,
                    limit=args.limit,
                    reviewed_only=not args.include_unreviewed,
                )
                print(
                    json.dumps(
                        {
                            "schema": "trufagent.skills.search.v2",
                            "query": args.query,
                            "matches": [
                                match.model_dump(mode="json") for match in matches
                            ],
                        }
                    )
                )
            elif args.skills_command == "audit":
                report = audit_skill_catalog(repository.load())
                save_json_document(args.report, report.model_dump_json(indent=2, by_alias=True))
                print(
                    json.dumps(
                        {
                            "status": "success",
                            "report": str(args.report),
                            "entries": len(report.entries),
                            "reviewed": sum(entry.reviewed for entry in report.entries),
                            "candidates": sum(
                                entry.disposition == "candidate" for entry in report.entries
                            ),
                            "review": sum(
                                entry.disposition == "review" for entry in report.entries
                            ),
                            "blocked": sum(
                                entry.disposition == "blocked" for entry in report.entries
                            ),
                        }
                    )
                )
            elif args.skills_command == "sources":
                catalog = repository.load()
                registry = sync_pilot_sources(
                    {entry.fingerprint for entry in catalog.entries}
                )
                save_json_document(
                    args.registry, registry.model_dump_json(indent=2, by_alias=True)
                )
                print(
                    json.dumps(
                        {
                            "status": "success",
                            "registry": str(args.registry),
                            "sources": len(registry.sources),
                        }
                    )
                )
            elif args.skills_command == "sanitize":
                if args.plan:
                    audit = SkillAuditReport.model_validate_json(
                        args.audit.read_text(encoding="utf-8")
                    )
                    manifest = plan_skill_sanitization(
                        repository.load(), audit, archive_root=args.archive_root
                    )
                    save_json_document(
                        args.manifest, manifest.model_dump_json(indent=2, by_alias=True)
                    )
                    tiers = {
                        tier: sum(entry.tier == tier for entry in manifest.entries)
                        for tier in ("core", "profile", "cold", "quarantine")
                    }
                    print(
                        json.dumps(
                            {
                                "status": "planned",
                                "manifest": str(args.manifest),
                                "entries": len(manifest.entries),
                                "tiers": tiers,
                                "mutations": 0,
                            }
                        )
                    )
                else:
                    manifest = SkillSanitizationManifest.model_validate_json(
                        args.apply.read_text(encoding="utf-8")
                    )
                    catalog = repository.load()
                    result = apply_skill_sanitization(
                        manifest,
                        catalog,
                        movable_roots=[
                            Path.home() / ".codex" / "skills",
                            Path.home() / ".claude" / "skills",
                        ],
                    )
                    repository.save(catalog)
                    roots, metadata = default_skill_roots(Path.home())
                    synced = repository.sync(
                        SkillDiscovery(roots, root_metadata=metadata).scan().catalog
                    )
                    print(
                        json.dumps(
                            {
                                "status": "applied",
                                **result,
                                "catalog_entries": len(synced.entries),
                                "recoverable": True,
                            }
                        )
                    )
            elif args.skills_command == "import":
                if not args.direct and not args.adapt:
                    raise ValueError("at least one --direct or --adapt selector is required")
                registry = RemoteSkillRegistry.model_validate_json(
                    args.sources.read_text(encoding="utf-8")
                )
                manifest = plan_skill_import(
                    registry,
                    direct=args.direct,
                    adapt=args.adapt,
                    vendor_root=args.vendor_root,
                    adaptation_root=args.adaptation_root,
                )
                save_json_document(
                    args.manifest, manifest.model_dump_json(indent=2, by_alias=True)
                )
                print(
                    json.dumps(
                        {
                            "status": "planned",
                            "manifest": str(args.manifest),
                            "items": len(manifest.items),
                            "direct": sum(item.mode == "direct" for item in manifest.items),
                            "adapt": sum(item.mode == "adapt" for item in manifest.items),
                            "mutations": 0,
                        }
                    )
                )
            else:
                surface = plan_codex_skill_surface(repository.load(), args.skill_root)
                if args.apply:
                    apply_managed_skill_surface(args.config, surface)
                print(
                    json.dumps(
                        {
                            "status": "applied" if args.apply else "planned",
                            "platform": args.platform,
                            "daily": surface.daily,
                            "daily_count": len(surface.daily),
                            "library_count": len(surface.library),
                            "config": str(args.config),
                        }
                    )
                )
        except (OSError, KeyError, ValueError, ValidationError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        return 0

    if args.command == "init":
        try:
            config = initialize_project(
                args.project_root,
                project=args.project,
                catalog_path=args.catalog,
            )
        except (OSError, ValueError, MemoryVaultError, ProjectInitializationError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(json.dumps({"status": "success", "config": str(config)}))
        return 0

    if args.command == "promotion":
        from trufagent.application.promotion import evaluate_promotion_readiness
        from trufagent.infrastructure.promotion_fs import (
            PromotionPolicyError,
            collect_promotion_facts,
            initialize_pilot_policy,
            load_promotion_policy,
        )
        from trufagent.infrastructure.promotion_review import (
            PromotionReviewError,
            approve_promotion_review,
            create_promotion_review,
        )
        from trufagent.infrastructure.promotion_workspace import prepare_promotion_workspace

        try:
            if args.promotion_command == "init":
                path = initialize_pilot_policy(args.project_root)
                print(json.dumps({"status": "success", "policy": str(path)}))
                return 0
            if args.promotion_command == "workspace":
                policy = load_promotion_policy(args.project_root)
                workspace = prepare_promotion_workspace(args.project_root, policy)
                print(workspace.model_dump_json(by_alias=True))
                return 0
            if args.promotion_command == "review":
                review = create_promotion_review(args.project_root)
                print(review.model_dump_json(by_alias=True))
                return 0
            if args.promotion_command == "approve":
                review = approve_promotion_review(
                    args.project_root,
                    args.confirm_review_id,
                )
                print(review.model_dump_json(by_alias=True))
                return 0
            if args.promotion_command == "pilot-begin":
                record = begin_pilot_task(args.project_root, args.task_id, args.kind)
                print(record.model_dump_json(by_alias=True))
                return 0
            if args.promotion_command == "pilot-finish":
                record = finish_pilot_task(args.project_root, args.task_id, args.status)
                print(record.model_dump_json(by_alias=True))
                return int(record.status != PilotTaskStatus.PASSED)
            policy = load_promotion_policy(args.project_root)
            facts = collect_promotion_facts(args.project_root, policy)
            readiness = evaluate_promotion_readiness(policy, facts)
            print(readiness.model_dump_json(by_alias=True))
            return int(not readiness.ready)
        except (
            OSError,
            ValueError,
            ValidationError,
            PromotionPolicyError,
            PromotionReviewError,
            PilotLedgerError,
        ) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1

    if args.command == "session":
        sessions = FileSessionRepository(args.project_root)
        try:
            if args.session_command == "start":
                project = _project(args.project_root, args.project)
                result = StartSessionService(sessions).start(
                    StartSessionRequest(project=project, objective=args.objective)
                )
                print(result.model_dump_json())
            elif args.session_command == "status":
                current = sessions.current()
                if current is None:
                    print(json.dumps({"status": "idle"}))
                else:
                    print(current.model_dump_json(by_alias=True))
            else:
                project = _project(args.project_root, args.project)
                request = EndSessionRequest.model_validate_json(
                    args.request.read_text(encoding="utf-8")
                )
                memory = MarkdownMemoryRepository(args.project_root, project=project).initialize()
                result = EndSessionService(sessions, memory).end(request)
                print(result.model_dump_json())
        except (OSError, ValueError, ValidationError, MemoryVaultError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        return 0

    if args.command == "memory" and args.memory_command == "validate":
        try:
            document = load_memory_markdown_compatible(args.path)
        except (OSError, MemoryFormatError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "status": "success",
                    "summary": f"valid memory: {document.envelope.id}",
                    "next_actions": [],
                    "artifacts": [str(args.path)],
                }
            )
        )
        return 0

    if args.command == "memory" and args.memory_command == "propose":
        repository = MarkdownMemoryRepository(
            args.project_root,
            project=args.project,
            user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
        ).initialize()
        try:
            raw = args.document.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            if len(parts) != 3:
                raise MemoryFormatError("expected YAML frontmatter delimited by ---")
            frontmatter = yaml.safe_load(parts[1])
            if not isinstance(frontmatter, dict):
                raise MemoryFormatError("frontmatter must be a YAML mapping")
            schema = frontmatter.get("schema")
            if schema == "trufagent.memory.v2":
                document = load_memory_markdown_compatible(args.document)
                v2_repository = MarkdownMemoryRepositoryV2(
                    args.project_root, project=args.project
                ).initialize()
                path = v2_repository.propose(document)
                SqliteMemoryIndex(
                    Path(args.project_root) / ".trufagent" / "memory-index.sqlite3"
                ).rebuild([*repository.documents(), *v2_repository.documents()])
            else:
                document = load_memory_markdown(args.document)
                if document.envelope.status.value != "proposed":
                    raise ValueError("memory propose requires status proposed")
                path = repository.propose(document)
        except (
            OSError,
            ValueError,
            MemoryFormatError,
            MemoryVaultError,
            yaml.YAMLError,
        ) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        print(
            json.dumps({"status": "proposed", "memory_id": document.envelope.id, "path": str(path)})
        )
        return 0

    if args.command == "task":
        try:
            root = args.root.resolve()
            project = _project(root, args.project)
            overrides = {
                field: value
                for field, value in {
                    "kind": args.kind,
                    "cause_known": args.cause_known,
                    "solution_known": args.solution_known,
                    "approved_plan": args.approved_plan,
                    "open_decisions": args.open_decisions,
                    "localized": args.localized,
                }.items()
                if value is not None
            }
            task_digest = hashlib.sha256(args.task.encode()).hexdigest()
            sessions = FileSessionRepository(root)
            session = StartSessionService(sessions).start(
                StartSessionRequest(
                    project=project,
                    objective=f"Personal task {task_digest[:12]}",
                )
            )
            repository = MarkdownMemoryRepository(
                root,
                project=project,
                user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
            ).initialize()
            planner = PlanTaskService(
                repository,
                cartography=GraphifyAdapter(),
                skills=_runtime_catalog(root, None),
            )
            prepared = PrepareTaskService(planner).prepare(
                PrepareTaskRequest(
                    intake=TaskIntake(
                        task=args.task,
                        signal_overrides=overrides,
                        required_symbols=args.required_symbol,
                    ),
                    project=project,
                    project_root=root,
                    include_user_memory=args.include_user_memory,
                    use_skills=args.use_skill,
                    without_skills=args.without_skill,
                )
            )
            extraction = prepared.extraction
            if prepared.plan is None:
                output = {
                    "schema": "trufagent.task-preview.v1",
                    "status": "needs-input",
                    "session_id": session.state.id,
                    "project": project,
                    "task": args.task,
                    "signals": extraction.signals.model_dump(mode="json"),
                    "inferences": [item.model_dump(mode="json") for item in extraction.evidence],
                    "questions": [item.model_dump(mode="json") for item in extraction.questions],
                    "next_action": "Answer the blocking questions, then rerun with corrections.",
                }
                print(json.dumps(output))
                return 2
            plan = prepared.plan
            preview_id = f"tp_{secrets.token_hex(10)}"
            preview_record = TaskPreviewRecord(
                schema="trufagent.task-preview-record.v1",
                preview_id=preview_id,
                session_id=session.state.id,
                project=project,
                task_digest=task_digest,
                worktree_fingerprint=fingerprint_worktree(root),
                created_at=datetime.now(UTC),
                summary=plan.summary,
                signals=extraction.signals,
                route=plan.model_route,
                skills=tuple(item.name for item in plan.selected_skills),
                memory_ids=tuple(item.memory_id for item in plan.context.items),
                required_symbols=tuple(dict.fromkeys(args.required_symbol)),
                structural_targets=tuple(
                    dict.fromkeys(item.label for item in plan.context.cartography.nodes)
                )
                if plan.context.cartography
                else (),
                graph_state=(
                    plan.context.cartography.graph_state.value
                    if plan.context.cartography
                    else None
                ),
                graph_commit=(
                    plan.context.cartography.graph_commit
                    if plan.context.cartography
                    else None
                ),
                graphify_version=(
                    plan.context.cartography.graphify_version
                    if plan.context.cartography
                    else None
                ),
                warnings=tuple(plan.warnings),
                autonomy=plan.strategy.autonomy_boundary,
                evidence_required=tuple(plan.strategy.evidence_required),
                exploration_disposition=(
                    plan.exploration_gate.disposition.value if plan.exploration_gate else None
                ),
                exploration_reasons=(
                    tuple(plan.exploration_gate.reasons) if plan.exploration_gate else ()
                ),
            )
            FileTaskPreviewRepository(root).save(preview_record)
            output = {
                "schema": "trufagent.task-preview.v1",
                "status": "ready",
                "preview_id": preview_id,
                "session_id": session.state.id,
                "project": project,
                "task": args.task,
                "summary": plan.summary,
                "signals": extraction.signals.model_dump(mode="json"),
                "inferences": [item.model_dump(mode="json") for item in extraction.evidence],
                "route": plan.model_route.model_dump(mode="json"),
                "exploration_gate": (
                    {
                        "disposition": plan.exploration_gate.disposition.value,
                        "reasons": list(plan.exploration_gate.reasons),
                    }
                    if plan.exploration_gate
                    else None
                ),
                "skills": [item.name for item in plan.selected_skills],
                "memory": [item.memory_id for item in plan.context.items],
                "required_symbols": list(dict.fromkeys(args.required_symbol)),
                "structural_targets": list(
                    dict.fromkeys(item.label for item in plan.context.cartography.nodes)
                )
                if plan.context.cartography
                else [],
                "warnings": plan.warnings,
                "autonomy": plan.strategy.autonomy_boundary.value,
                "evidence_required": plan.strategy.evidence_required,
                "next_action": (
                    "Proceed locally with the selected skills and evidence gates."
                    if plan.strategy.autonomy_boundary.value in {"proceed", "announce"}
                    else "Review the preview before any implementation or provider call."
                ),
                "continuations": {
                    "local": (
                        f"trufagent task-continue {preview_id} "
                        f"--root {shlex.quote(str(root))} --mode local"
                    ),
                    "shadow": (
                        f"trufagent task-continue {preview_id} "
                        f"--root {shlex.quote(str(root))} --mode shadow"
                    ),
                },
            }
            print(json.dumps(output))
            return 0
        except (
            OSError,
            ValueError,
            ValidationError,
            GraphifyAdapterError,
            MemoryVaultError,
            yaml.YAMLError,
        ) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1

    if args.command == "memory":
        repository = MarkdownMemoryRepository(
            args.project_root,
            project=args.project,
            user_memory_root=Path.home() / ".trufagent" / "memory" / "user",
        ).initialize()
        index = SqliteMemoryIndex(Path(args.project_root) / ".trufagent" / "memory-index.sqlite3")
        review = MemoryReviewService(repository, index=index)
        v2_repository = MarkdownMemoryRepositoryV2(
            args.project_root, project=args.project
        ).initialize()
        review_v2 = MemoryV2Service(
            v2_repository,
            index=index,
            legacy_documents=repository.documents,
        )
        try:
            if args.memory_command == "list":
                documents = [*repository.documents(), *v2_repository.documents()]
                if args.status:
                    documents = [
                        document
                        for document in documents
                        if document.envelope.status.value == args.status
                    ]
                print(
                    json.dumps(
                        [
                            {
                                "id": document.envelope.id,
                                "title": document.envelope.title,
                                "kind": document.envelope.kind.value,
                                "status": document.envelope.status.value,
                                "governs": document.envelope.governs_behavior,
                            }
                            for document in documents
                        ]
                    )
                )
            elif args.memory_command == "show":
                try:
                    document = v2_repository.read(args.memory_id)
                except KeyError:
                    document = repository.read(args.memory_id)
                print(document.model_dump_json())
            elif args.memory_command == "history":
                try:
                    events = v2_repository.events(args.memory_id)
                    v2_repository.read(args.memory_id)
                except KeyError:
                    events = review.history(args.memory_id)
                print(
                    json.dumps(
                        [
                            event.model_dump(by_alias=True, mode="json")
                            for event in events
                        ]
                    )
                )
            elif args.memory_command == "accept":
                try:
                    v2_repository.read(args.memory_id)
                except KeyError:
                    metadata = (
                        MemoryReviewMetadata.model_validate_json(
                            args.metadata.read_text(encoding="utf-8")
                        )
                        if args.metadata
                        else None
                    )
                    result = review.accept(
                        args.memory_id,
                        reviewer=args.reviewer,
                        metadata=metadata,
                    )
                else:
                    if args.metadata:
                        raise ValueError("v2 accept does not use extended metadata")
                    result = review_v2.accept(args.memory_id, reviewer=args.reviewer)
                print(result.model_dump_json())
            elif args.memory_command == "replace":
                print(
                    review_v2.replace(
                        args.memory_id,
                        replacement_id=args.replacement_id,
                        reviewer=args.reviewer,
                        reason=args.reason,
                    ).model_dump_json()
                )
            elif args.memory_command == "retire":
                print(
                    review_v2.retire(
                        args.memory_id,
                        reviewer=args.reviewer,
                        reason=args.reason,
                    ).model_dump_json()
                )
            elif args.memory_command == "reject":
                print(
                    review.reject(
                        args.memory_id,
                        reviewer=args.reviewer,
                        reason=args.reason,
                    ).model_dump_json()
                )
            else:
                print(
                    review.supersede(
                        args.memory_id,
                        replacement_id=args.replacement_id,
                        reviewer=args.reviewer,
                        reason=args.reason,
                    ).model_dump_json()
                )
        except (OSError, KeyError, ValueError, MemoryVaultError) as exc:
            print(json.dumps({"status": "error", "summary": str(exc)}), file=sys.stderr)
            return 1
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
