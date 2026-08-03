from pathlib import Path

import pytest

from trufagent.domain.memory import MemoryKind, MemoryStatus, memory_json_schema
from trufagent.infrastructure.memory_markdown import (
    MemoryFormatError,
    SecretShapeError,
    load_memory_markdown,
    parse_memory_markdown,
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
