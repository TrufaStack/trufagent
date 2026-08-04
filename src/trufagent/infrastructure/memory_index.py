from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from trufagent.domain.memory import MemoryDocument
from trufagent.domain.memory_v2 import MemoryDocumentV2


class MemorySearchHit(BaseModel):
    memory_id: str
    source_path: str
    score: float


class SqliteMemoryIndex:
    """Disposable FTS5 projection of canonical Markdown memory."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def rebuild(self, documents: Iterable[MemoryDocument | MemoryDocumentV2]) -> int:
        rows = list(documents)
        with self._connect() as connection:
            connection.execute("DROP TABLE IF EXISTS memories")
            connection.execute(
                """
                CREATE VIRTUAL TABLE memories USING fts5(
                    memory_id UNINDEXED,
                    project UNINDEXED,
                    status UNINDEXED,
                    source_path UNINDEXED,
                    title,
                    body,
                    tags,
                    applicability
                )
                """
            )
            connection.executemany(
                "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.envelope.id,
                        item.envelope.project,
                        item.envelope.status.value,
                        item.source_path or "",
                        item.envelope.title,
                        item.body,
                        " ".join(item.envelope.tags),
                        " ".join(
                            item.envelope.applies_when.concepts
                            + item.envelope.applies_when.paths
                            + item.envelope.applies_when.symbols
                            + item.envelope.applies_when.technologies
                            + item.envelope.applies_when.operations
                        )
                        if isinstance(item, MemoryDocument)
                        else "",
                    )
                    for item in rows
                ],
            )
        return len(rows)

    def search(self, query: str, *, project: str, limit: int = 10) -> list[MemorySearchHit]:
        terms = re.findall(r"\w+", query)
        if not terms or not self.path.exists():
            return []
        expression = " OR ".join(f'"{term}"' for term in terms)
        with self._connect() as connection:
            records = connection.execute(
                """
                SELECT memory_id, source_path, bm25(memories)
                FROM memories
                WHERE memories MATCH ?
                  AND (project = ? OR project = '*')
                  AND status NOT IN ('rejected', 'superseded', 'stale', 'replaced', 'retired')
                ORDER BY bm25(memories), memory_id
                LIMIT ?
                """,
                (expression, project, limit),
            ).fetchall()
        return [
            MemorySearchHit(memory_id=row[0], source_path=row[1], score=-float(row[2]))
            for row in records
        ]
