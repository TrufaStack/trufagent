from pathlib import Path

from trufagent.application.context_builder import ContextBuilder, ContextRequest
from trufagent.domain.cartography import GraphQueryResult
from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_markdown import load_memory_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


class FakeCartography:
    question = ""

    def query(self, project_root: Path, question: str, *, token_budget: int) -> GraphQueryResult:
        self.question = question
        return GraphQueryResult(
            summary="NODE saveChecklist [src=src/save.py loc=10 community=Persistence]",
            graphify_version="0.9.30",
            graph_commit="abc123",
        )


def test_packet_prioritizes_critical_rule_and_relevant_risk(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(
        tmp_path, project="jc-app", user_memory_root=tmp_path / "user-memory"
    )
    repository.initialize()
    for name in (
        "c02-checklist-risk.md",
        "c05-safe-diagnostics-rule.md",
        "c09-greendeal-negative-decision.md",
    ):
        repository.propose(load_memory_markdown(FIXTURES / name))

    packet = ContextBuilder(repository).build(
        ContextRequest(
            query="debug checklist routing with environment variables",
            project="jc-app",
            token_budget=1_000,
            include_user=True,
        )
    )

    assert [item.memory_id for item in packet.items[:2]] == [
        "mem_C05_SAFE_DIAGNOSTICS",
        "mem_C02_CHECKLIST_RISK",
    ]
    assert all(item.governs_behavior for item in packet.items[:2])
    assert packet.estimated_tokens <= 1_000


def test_proposed_memory_can_warn_but_cannot_govern(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    repository.propose(load_memory_markdown(FIXTURES / "c10-mobile-artifact.md"))

    packet = ContextBuilder(repository).build(
        ContextRequest(query="implement mobile navigation design", project="jc-app")
    )

    assert packet.items[0].memory_id == "mem_C10_MOBILE_ARTIFACT"
    assert packet.items[0].governs_behavior is False
    assert any("unreviewed" in warning for warning in packet.items[0].warnings)


def test_packet_respects_small_budget_without_truncating_documents(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(
        tmp_path, project="jc-app", user_memory_root=tmp_path / "user-memory"
    )
    repository.initialize()
    for name in ("c02-checklist-risk.md", "c05-safe-diagnostics-rule.md"):
        repository.propose(load_memory_markdown(FIXTURES / name))

    packet = ContextBuilder(repository).build(
        ContextRequest(
            query="checklist password shell",
            project="jc-app",
            token_budget=120,
            include_user=True,
        )
    )

    assert len(packet.items) == 1
    assert packet.omitted_count == 1
    assert packet.estimated_tokens <= 120


def test_packet_keeps_cartography_separate_from_governing_memory(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    repository.propose(load_memory_markdown(FIXTURES / "c02-checklist-risk.md"))

    packet = ContextBuilder(repository, cartography=FakeCartography()).build(
        ContextRequest(
            query="where is checklist saved?",
            project="jc-app",
            project_root=tmp_path,
            cartography_token_budget=300,
        )
    )

    assert packet.cartography is not None
    assert packet.cartography.graphify_version == "0.9.30"
    assert packet.items[0].governs_behavior is True
    assert all(item.memory_id != "graphify" for item in packet.items)


def test_packet_can_use_a_precise_cartography_query_without_changing_memory_query(
    tmp_path: Path,
) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    cartography = FakeCartography()

    packet = ContextBuilder(repository, cartography=cartography).build(
        ContextRequest(
            query="Verify the local-only database bootstrap.",
            cartography_query="assertLocalDatabaseUrl",
            project="jc-app",
            project_root=tmp_path,
        )
    )

    assert packet.query == "Verify the local-only database bootstrap."
    assert cartography.question == "assertLocalDatabaseUrl"


def test_packet_can_intentionally_abstain_from_cartography(
    tmp_path: Path,
) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    cartography = FakeCartography()

    packet = ContextBuilder(repository, cartography=cartography).build(
        ContextRequest(
            query="Choose an architecture.",
            project="jc-app",
            project_root=tmp_path,
            query_cartography=False,
        )
    )

    assert packet.cartography is None
    assert cartography.question == ""
    assert packet.warnings == []
