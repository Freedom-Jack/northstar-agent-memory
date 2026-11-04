"""Northstar's core: the stores, events and ports every part builds on (MEMORY-ARCHITECTURE §2, §3).

The core makes no model calls. Code decides; models only propose, through proposals the write gate checks.

What is exported here is what the parts above the core use: the ports and their records, the SQLite adapters, the write
gate with its projector, the invariants and the replay check. The submodules hold the rest.
"""

from northstar_agent_memory.core.db import STORES, EncryptionRequired, open_store, transaction
from northstar_agent_memory.core.events import EventEnvelope, make_event, validate
from northstar_agent_memory.core.gate import GateResult, UserAuthority, WriteGate
from northstar_agent_memory.core.history import HistoryConflict, SQLiteHistoryStore
from northstar_agent_memory.core.ids import new_id, utc_now
from northstar_agent_memory.core.index_store import SQLiteIndexStore
from northstar_agent_memory.core.invariants import INVARIANTS, Violation, sweep
from northstar_agent_memory.core.overview_store import SQLiteOverviewStore
from northstar_agent_memory.core.ports import (
    ApplyResult,
    EvidenceQuote,
    HistoryStore,
    IndexPort,
    MemoryReader,
    MemoryWriter,
    ModelCall,
    OverviewStore,
    Projector as ProjectorPort,
    Proposal,
    Rejection,
    RunStore,
    SearchHit,
    SearchQuery,
    Verdict,
    WorkingStore,
)
from northstar_agent_memory.core.projector import ProjectionError, Projector
from northstar_agent_memory.core.reader import SQLiteMemoryReader
from northstar_agent_memory.core.replay import canonical_hash, rebuild, verify_replay
from northstar_agent_memory.core.runs import SQLiteRunStore
from northstar_agent_memory.core.working import SQLiteWorkingStore

__all__ = [
    "INVARIANTS", "STORES", "ApplyResult", "EncryptionRequired", "EventEnvelope", "EvidenceQuote", "GateResult", "HistoryConflict",
    "HistoryStore", "IndexPort", "MemoryReader", "MemoryWriter", "ModelCall", "OverviewStore", "ProjectionError",
    "Projector", "ProjectorPort", "Proposal", "Rejection", "RunStore", "SQLiteHistoryStore", "SQLiteIndexStore",
    "SQLiteMemoryReader", "SQLiteOverviewStore", "SQLiteRunStore", "SQLiteWorkingStore", "SearchHit", "SearchQuery",
    "UserAuthority", "Verdict", "Violation", "WorkingStore", "WriteGate", "canonical_hash", "make_event", "new_id", "open_store",
    "rebuild", "sweep", "transaction", "utc_now", "validate", "verify_replay",
]  # fmt: skip
