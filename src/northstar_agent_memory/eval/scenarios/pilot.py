"""The pilot persona: one hand-written development persona covering all 18 scenarios
(SYNTHESIS §9 item 2; note 09, Implications §7, Stage 0).

Invented content only. The persona lives in data/pilot/ as several JSON files, so that a
run that stops part-way keeps what it wrote: persona.json, sessions_NN.json (compact
sessions, expanded here), gold.json, updates.json and probes.json. A file that is missing
adds nothing, and `validate` says what is then incomplete.
"""

from __future__ import annotations

import json
from pathlib import Path

from northstar_agent_memory.eval.scenarios.ledger import (
    Persona,
    Project,
    World,
    fill_question_dates,
    memory_from_script,
    probe_from_script,
    source_from_script,
    update_from_script,
)

DATA_DIR = Path(__file__).parent / "data" / "pilot"


def _read(directory: Path, name: str, default):
    path = directory / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def load_pilot(data_dir: Path = DATA_DIR) -> World:
    """Merge the pilot's files into one World."""
    header = _read(data_dir, "persona.json", None)
    if header is None:
        raise FileNotFoundError(f"no persona.json in {data_dir}")
    persona = header["persona"]
    world = World(
        id=header["id"],
        persona=Persona(
            name=persona["name"],
            summary=persona.get("summary", ""),
            projects=[Project(**p) for p in persona.get("projects", [])],
            traits=list(persona.get("traits", [])),
        ),
        sessions=[],
        gold_memories=[],
        gold_updates=[],
        probes=[],
        meta=dict(header.get("meta", {})),
    )
    for path in sorted(data_dir.glob("sessions_*.json")):
        world.sessions.extend(source_from_script(s) for s in json.loads(path.read_text(encoding="utf-8")))
    world.sessions.sort(key=lambda s: s.started_at or "")
    for spec in _read(data_dir, "gold.json", []):
        memory, tags = memory_from_script(spec)
        world.gold_memories.append(memory)
        world.tags[memory.key] = tags
    for spec in _read(data_dir, "updates.json", []):
        update, tags = update_from_script(spec)
        world.gold_updates.append(update)
        world.tags[update.key] = tags
    for spec in _read(data_dir, "probes.json", []):
        probe, tags = probe_from_script(world.id, spec)
        world.probes.append(probe)
        world.tags[probe.id] = tags
    fill_question_dates(world)
    return world
