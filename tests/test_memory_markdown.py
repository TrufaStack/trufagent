from pathlib import Path

import pytest

from trufagent.domain.memory import MemoryKind, MemoryStatus, memory_json_schema
from trufagent.domain.memory_v2 import MemoryStateV2, memory_v2_json_schema
from trufagent.infrastructure.memory_markdown import (
    MemoryFormatError,
    SecretShapeError,
    load_memory_markdown,
    load_memory_markdown_compatible,
    parse_memory_markdown,
    parse_memory_markdown_compatible,
)

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


@pytest.mark.parametrize(
    ("filename", "kind"),
    [
        ("c02-checklist-risk.md", MemoryKind.RISK),
        ("c05-safe-diagnostics-rule.md", MemoryKind.RULE),
        ("c09-greendeal-negative-decision.md", MemoryKind.NEGATIVE_DECISION),
        ("c10-mobile-artifact.md", MemoryKind.EXTERNAL_ARTIFACT),
    ],
)
def test_casebook_fixtures_load(filename: str, kind: MemoryKind) -> None:
    document = load_memory_markdown(FIXTURES / filename)

    assert document.envelope.kind == kind
    assert document.body


def test_accepted_reviewed_rule_governs_behavior() -> None:
    document = load_memory_markdown(FIXTURES / "c05-safe-diagnostics-rule.md")

    assert document.envelope.governs_behavior is True


def test_proposed_artifact_does_not_govern_behavior() -> None:
    document = load_memory_markdown(FIXTURES / "c10-mobile-artifact.md")

    assert document.envelope.status == MemoryStatus.PROPOSED
    assert document.envelope.governs_behavior is False


def test_secret_shape_is_rejected() -> None:
    raw = (FIXTURES / "c05-safe-diagnostics-rule.md").read_text()
    unsafe = raw.replace(
        "Los diagnósticos consultan presencia o estado",
        "password=correct-horse-battery-staple\n\nLos diagnósticos consultan presencia o estado",
    )

    with pytest.raises(SecretShapeError, match="password-assignment"):
        parse_memory_markdown(unsafe)


def test_accepted_unreviewed_rule_is_rejected() -> None:
    raw = (FIXTURES / "c05-safe-diagnostics-rule.md").read_text()
    invalid = raw.replace("trust: human-reviewed", "trust: unreviewed").replace(
        "reviewed_by: user", "reviewed_by:"
    )

    with pytest.raises(MemoryFormatError, match="requires human review"):
        parse_memory_markdown(invalid)


def test_memory_schema_uses_canonical_alias() -> None:
    schema = memory_json_schema()

    assert "schema" in schema["properties"]
    assert "schema_" not in schema["properties"]


def test_v2_memory_uses_compact_canonical_schema() -> None:
    document = load_memory_markdown_compatible(FIXTURES / "v2-compact-decision.md")
    schema = memory_v2_json_schema()

    assert document.envelope.status == MemoryStateV2.ACCEPTED
    assert document.envelope.governs_behavior is True
    assert document.envelope.tags == ["memory", "v2"]
    assert set(schema["properties"]) == {
        "schema",
        "id",
        "kind",
        "title",
        "status",
        "project",
        "created_at",
        "updated_at",
        "reviewed_by",
        "source_commit",
        "tags",
    }


def test_v1_memory_projects_to_the_same_compact_contract() -> None:
    document = load_memory_markdown_compatible(FIXTURES / "c05-safe-diagnostics-rule.md")

    assert document.envelope.schema_ == "trufagent.memory.v2"
    assert document.envelope.kind == MemoryKind.RULE
    assert document.envelope.status == MemoryStateV2.ACCEPTED
    assert document.envelope.governs_behavior is True
    assert document.source_path.endswith("c05-safe-diagnostics-rule.md")


def test_accepted_v2_memory_requires_human_review() -> None:
    raw = (
        (FIXTURES / "v2-compact-decision.md")
        .read_text()
        .replace("reviewed_by: user", "reviewed_by:")
    )

    with pytest.raises(MemoryFormatError, match="requires human review"):
        parse_memory_markdown_compatible(raw)


def test_compatible_reader_rejects_unknown_schema() -> None:
    raw = (
        (FIXTURES / "v2-compact-decision.md")
        .read_text()
        .replace("trufagent.memory.v2", "trufagent.memory.v3")
    )

    with pytest.raises(MemoryFormatError, match="unsupported memory schema"):
        parse_memory_markdown_compatible(raw)
