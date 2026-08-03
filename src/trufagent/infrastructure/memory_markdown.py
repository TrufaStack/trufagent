from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from trufagent.domain.memory import MemoryDocument, MemoryEnvelope

_FRONTMATTER = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)\Z", re.DOTALL)
_SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "provider-token": re.compile(r"\b(?:sk|ghp|glpat)-[A-Za-z0-9_-]{16,}\b"),
    "password-assignment": re.compile(
        r"(?im)^\s*(?:password|passwd|db_password|database_password)"
        r"""\s*[:=]\s*["']?[^ \t\r\n"']{6,}"""
    ),
    "credential-url": re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s/]+@", re.IGNORECASE),
}


class MemoryFormatError(ValueError):
    """Raised when a canonical memory document cannot be parsed safely."""


class SecretShapeError(MemoryFormatError):
    """Raised when a document appears to contain a secret value."""

    def __init__(self, shapes: list[str]) -> None:
        self.shapes = shapes
        super().__init__(f"memory contains forbidden secret shapes: {', '.join(shapes)}")


def find_secret_shapes(text: str) -> list[str]:
    return [name for name, pattern in _SECRET_PATTERNS.items() if pattern.search(text)]


def parse_memory_markdown(text: str, *, source_path: str | None = None) -> MemoryDocument:
    matches = _FRONTMATTER.match(text)
    if not matches:
        raise MemoryFormatError("expected YAML frontmatter delimited by ---")

    shapes = find_secret_shapes(text)
    if shapes:
        raise SecretShapeError(shapes)

    try:
        raw: Any = yaml.safe_load(matches.group("yaml"))
    except yaml.YAMLError as exc:
        raise MemoryFormatError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(raw, dict):
        raise MemoryFormatError("frontmatter must be a YAML mapping")

    body = matches.group("body").strip()
    if not body:
        raise MemoryFormatError("memory body cannot be empty")

    try:
        envelope = MemoryEnvelope.model_validate(raw)
    except ValidationError as exc:
        raise MemoryFormatError(str(exc)) from exc

    return MemoryDocument(envelope=envelope, body=body, source_path=source_path)


def load_memory_markdown(path: Path) -> MemoryDocument:
    return parse_memory_markdown(path.read_text(encoding="utf-8"), source_path=str(path))
