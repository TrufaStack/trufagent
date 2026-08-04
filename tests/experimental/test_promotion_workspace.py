from pathlib import Path

from trufagent.experimental.promotion_fs import (
    collect_promotion_facts,
    initialize_pilot_policy,
    load_promotion_policy,
)
from trufagent.experimental.promotion_workspace import (
    load_promotion_workspace,
    operation_gate_is_enforced,
    prepare_promotion_workspace,
)


def test_prepare_workspace_is_sanitized_isolated_and_non_applicable(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    (source / ".env").write_text("TOKEN=excluded\n")
    initialize_pilot_policy(source)
    policy = load_promotion_policy(source)

    record = prepare_promotion_workspace(
        source,
        policy,
        workspace_base=tmp_path / "workspaces",
    )

    assert record.workspace_root != source
    assert (record.workspace_root / "app.py").read_text() == "VALUE = 1\n"
    assert not (record.workspace_root / ".env").exists()
    assert record.source_write_allowed is False
    assert record.apply_allowed is False
    assert load_promotion_workspace(source) == record
    assert collect_promotion_facts(source, policy).isolated_write_worktree is True
    assert operation_gate_is_enforced(source) is True


def test_operation_gate_fails_closed_when_boundary_is_tampered(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    initialize_pilot_policy(source)
    policy = load_promotion_policy(source)
    record = prepare_promotion_workspace(
        source,
        policy,
        workspace_base=tmp_path / "workspaces",
    )
    boundary = record.workspace_root.parent / "execution-boundary.json"
    boundary.write_text(
        boundary.read_text().replace(
            '"network_allowed": false',
            '"network_allowed": true',
        )
    )

    assert operation_gate_is_enforced(source) is False
    assert collect_promotion_facts(source, policy).git_deploy_migration_gate is False


def test_workspace_evidence_fails_when_workspace_disappears(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    initialize_pilot_policy(source)
    policy = load_promotion_policy(source)
    record = prepare_promotion_workspace(
        source,
        policy,
        workspace_base=tmp_path / "workspaces",
    )
    record.workspace_root.rename(record.workspace_root.parent / "gone")

    try:
        load_promotion_workspace(source)
    except Exception as exc:
        assert str(exc) == "promotion workspace no longer exists"
    else:
        raise AssertionError("missing workspace evidence was accepted")
