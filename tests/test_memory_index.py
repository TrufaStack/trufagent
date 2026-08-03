from pathlib import Path

from trufagent.infrastructure.memory_fs import MarkdownMemoryRepository
from trufagent.infrastructure.memory_index import SqliteMemoryIndex
from trufagent.infrastructure.memory_markdown import load_memory_markdown

FIXTURES = Path(__file__).parent / "fixtures" / "memory"


def test_fts_index_rebuilds_from_canonical_documents(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(
        tmp_path, project="jc-app", user_memory_root=tmp_path / "user-memory"
    )
    repository.initialize()
    repository.propose(load_memory_markdown(FIXTURES / "c02-checklist-risk.md"))
    repository.propose(load_memory_markdown(FIXTURES / "c05-safe-diagnostics-rule.md"))
    index = SqliteMemoryIndex(tmp_path / ".trufagent" / "memory-index.sqlite3")

    indexed = index.rebuild(repository.documents(include_user=True))
    results = index.search("checklist table routing", project="jc-app")

    assert indexed == 2
    assert [result.memory_id for result in results] == ["mem_C02_CHECKLIST_RISK"]
    assert results[0].source_path.endswith("mem_C02_CHECKLIST_RISK.md")


def test_index_can_be_deleted_and_recreated_without_losing_memory(tmp_path: Path) -> None:
    repository = MarkdownMemoryRepository(tmp_path, project="jc-app")
    repository.initialize()
    document = load_memory_markdown(FIXTURES / "c02-checklist-risk.md")
    repository.propose(document)
    index_path = tmp_path / ".trufagent" / "memory-index.sqlite3"
    index = SqliteMemoryIndex(index_path)
    index.rebuild(repository.documents())
    index_path.unlink()

    SqliteMemoryIndex(index_path).rebuild(repository.documents())

    assert repository.read(document.envelope.id).body == document.body
