"""Neutral chat-history records, shared by capture, the harness and the core.

These mirror the `source` and `message` records of MEMORY-ARCHITECTURE §2.2. The
speaker always comes from the app's own role map, never from a model (I3), and the
text is kept word for word.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Literal

Speaker = Literal["user", "assistant", "tool", "northstar", "system"]
Origin = Literal[
    "typed",
    "pasted",
    "assistant_output",
    "tool_output",
    "model_reported",
    "northstar_injected",
]
SourceKind = Literal["chat", "work", "document", "northstar_output"]


@dataclass(slots=True)
class Message:
    """One captured turn."""

    id: str  # unique within a corpus, e.g. "<source_id>:<ordinal>"
    source_id: str
    ordinal: int  # position in the source, from 0
    speaker: Speaker
    text: str  # word for word
    occurred_at: str | None = None  # ISO 8601, local time with offset where known
    origin: Origin = "typed"
    agent: str | None = None  # the app or agent, e.g. "claude-code"
    model_family: str | None = None  # family of the AI that said it, for assistant turns
    branch: str | None = None
    meta: dict = field(default_factory=dict)  # never an input to ranking (I23)


@dataclass(slots=True)
class Source:
    """One conversation, document or piece of work."""

    id: str
    kind: SourceKind = "chat"
    app: str | None = None
    project: str | None = None  # the repository or folder
    title: str | None = None
    started_at: str | None = None
    messages: list[Message] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def user_messages(self) -> list[Message]:
        return [m for m in self.messages if m.speaker == "user"]

    def text_of(self, speakers: Iterable[str] = ("user", "assistant")) -> str:
        wanted = set(speakers)
        return "\n".join(f"{m.speaker}: {m.text}" for m in self.messages if m.speaker in wanted)


def source_to_dict(source: Source) -> dict:
    return asdict(source)


def source_from_dict(data: dict) -> Source:
    messages = [Message(**m) for m in data.get("messages", [])]
    rest = {k: v for k, v in data.items() if k != "messages"}
    return Source(messages=messages, **rest)


def dump_jsonl(sources: Iterable[Source], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for source in sources:
            fh.write(json.dumps(source_to_dict(source), ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> Iterator[Source]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield source_from_dict(json.loads(line))


def message_index(sources: Iterable[Source]) -> dict[str, Message]:
    """Map message id to message across sources."""
    return {m.id: m for s in sources for m in s.messages}
