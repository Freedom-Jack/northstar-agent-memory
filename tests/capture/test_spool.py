"""The spool: append-only day files, a watermark per file, torn lines, locks, scrubbing, the capture log."""

from __future__ import annotations

import json
import os
import stat
import sys
import threading
from pathlib import Path

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.capture import spool
from northstar_agent_memory.core.ids import is_ulid, ulid_time_ms

from . import assert_throwaway_root, FAKE_TOKEN, SESSION, T0


@pytest.fixture(autouse=True)
def _throwaway_root():
    assert_throwaway_root()
    yield
    assert_throwaway_root()


def rec(n: int = 0, at: float = T0, **payload) -> dict:
    return spool.make_record(
        "UserPromptSubmit", SESSION, {"prompt": f"turn {n}", **payload},
        transcript_path="/nowhere/t.jsonl", cwd="/x", now=at + n,
    )


# --- records ----------------------------------------------------------------------------------------------------


def test_a_ulid_is_a_valid_time_ordered_id_of_the_core_form():
    a, b = spool.new_ulid(1_000), spool.new_ulid(2_000)
    assert is_ulid(a) and is_ulid(b)
    assert ulid_time_ms(a) == 1_000
    assert a < b
    assert is_ulid(spool.new_ulid())


def test_a_record_holds_the_event_session_transcript_cwd_times_and_payload():
    r = spool.make_record("Stop", SESSION, {"last_assistant_message": "done"}, transcript_path="/t.jsonl", cwd="/p", now=T0)
    assert is_ulid(r["id"])
    assert (r["event"], r["session_id"], r["transcript_path"], r["cwd"]) == ("Stop", SESSION, "/t.jsonl", "/p")
    assert r["recorded_at"] == "2026-03-02T09:00:00.000Z"
    assert r["occurred_at"].startswith("2026-03-02T") and r["occurred_at"][-6] in "+-"  # local time with an offset
    assert r["scrub"] == "secrets" and r["payload"] == {"last_assistant_message": "done"}


# --- appending --------------------------------------------------------------------------------------------------


def test_append_writes_one_line_to_the_days_file_with_private_permissions():
    path = spool.append(rec(0))
    assert path == paths.data_root() / "spool" / "claude-code" / "2026-03-02.jsonl"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    lines = path.read_text(encoding="ascii").splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["payload"]["prompt"] == "turn 0"


def test_each_utc_day_gets_its_own_file():
    spool.append(rec(0, at=T0))
    spool.append(rec(1, at=T0 + 86400))
    assert [p.name for p in spool.spool_files()] == ["2026-03-02.jsonl", "2026-03-03.jsonl"]


def test_append_fsyncs(monkeypatch):
    calls = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(fd), real(fd))[1])
    spool.append(rec(0))
    assert len(calls) == 1


def test_text_of_any_script_round_trips_and_the_line_is_ascii():
    text = "naïve café — 日本語 😀 \"quotes\" \\ and\nnewlines\ttabs"
    spool.append(rec(0, prompt=text))
    (r,) = spool.read_pending()
    assert r.payload["prompt"] == text
    assert spool.spool_files()[0].read_bytes().isascii()


def test_concurrent_appends_never_interleave():
    def worker(k):
        for i in range(25):
            spool.append(rec(k * 100 + i, prompt="x" * 3000))

    threads = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    records, end, corrupt = spool.read_file(spool.spool_files()[0])
    assert (len(records), corrupt) == (200, 0)
    assert len({r.id for r in records}) == 200
    assert end == spool.spool_files()[0].stat().st_size


# --- reading and the watermark ---------------------------------------------------------------------------------------


def test_read_returns_records_in_file_order_with_their_end_offsets():
    for n in range(3):
        spool.append(rec(n))
    records = spool.read_pending()
    assert [r.payload["prompt"] for r in records] == ["turn 0", "turn 1", "turn 2"]
    assert [r.file for r in records] == ["2026-03-02.jsonl"] * 3
    assert records[-1].end == spool.spool_files()[0].stat().st_size
    assert records[0].end < records[1].end < records[2].end


def test_the_watermark_hides_what_was_handled():
    for n in range(3):
        spool.append(rec(n))
    path = spool.spool_files()[0]
    first, *_ = spool.read_file(path)[0]
    assert spool.watermark(path) == 0 and spool.has_pending()
    spool.set_watermark(path, first.end)
    assert [r.payload["prompt"] for r in spool.read_pending()] == ["turn 1", "turn 2"]
    spool.set_watermark(path, path.stat().st_size)
    assert spool.read_pending() == [] and not spool.has_pending()
    spool.append(rec(3))
    assert [r.payload["prompt"] for r in spool.read_pending()] == ["turn 3"] and spool.has_pending()


def test_an_unreadable_watermark_means_start_over(tmp_path):
    spool.append(rec(0))
    path = spool.spool_files()[0]
    (path.parent / (path.name + ".mark")).write_text("not a number")
    assert spool.watermark(path) == 0
    assert len(spool.read_pending()) == 1


def test_a_torn_last_line_is_left_alone_until_it_is_finished():
    path = spool.append(rec(0))
    spool.append(rec(1))
    first, whole = path.read_bytes().splitlines()
    path.write_bytes(first + b"\n" + whole[: len(whole) // 2])  # the second line is cut
    records, end, corrupt = spool.read_file(path)
    assert [r.payload["prompt"] for r in records] == ["turn 0"] and corrupt == 0
    assert end == len(first) + 1  # the watermark stops before the torn line
    spool.set_watermark(path, end)
    assert spool.has_pending()  # the torn bytes are still waiting
    with path.open("ab") as fh:  # the writer finishes its line after all
        fh.write(whole[len(whole) // 2 :] + b"\n")
    assert [r.payload["prompt"] for r in spool.read_pending()] == ["turn 1"]


def test_a_new_record_after_a_torn_line_starts_on_its_own_line_and_is_not_lost():
    spool.append(rec(0))
    path = spool.spool_files()[0]
    with path.open("ab") as fh:
        fh.write(b'{"v":1,"id":"01TORN","event":"Stop","sess')  # a hook killed mid-write
    spool.append(rec(1))
    records, end, corrupt = spool.read_file(path)
    assert [r.payload["prompt"] for r in records] == ["turn 0", "turn 1"]
    assert corrupt == 1  # the torn line, now complete but not a record
    assert end == path.stat().st_size


def test_lines_that_are_not_records_are_counted_and_skipped():
    spool.append(rec(0))
    path = spool.spool_files()[0]
    with path.open("ab") as fh:
        fh.write(b"not json\n")
        fh.write(b'["a", "list"]\n')
        fh.write(b'{"id": "x", "event": "Stop"}\n')  # missing fields
        fh.write(b'{"id":"x","event":"Stop","session_id":"s","recorded_at":"t","payload":"not a dict"}\n')
        fh.write(b"\n")
    spool.append(rec(1))
    records, end, corrupt = spool.read_file(path)
    assert [r.payload["prompt"] for r in records] == ["turn 0", "turn 1"] and corrupt == 4
    assert end == path.stat().st_size


def test_reading_from_a_file_that_vanished_is_empty(tmp_path):
    assert spool.read_file(tmp_path / "gone.jsonl", 0) == ([], 0, 0)


# --- pruning ----------------------------------------------------------------------------------------------------


def test_prune_deletes_only_fully_ingested_files_older_than_the_keep_time():
    old = spool.append(rec(0, at=T0))
    pending = spool.append(rec(0, at=T0 + 86400))
    spool.set_watermark(old, old.stat().st_size)
    now = old.stat().st_mtime + spool.DONE_KEEP_S + 10
    assert spool.prune(now=now) == 1
    assert [p.name for p in spool.spool_files()] == [pending.name]
    assert not (old.parent / (old.name + ".mark")).exists()


def test_prune_keeps_a_fresh_done_file_and_any_pending_one():
    done = spool.append(rec(0, at=T0))
    spool.set_watermark(done, done.stat().st_size)
    other = spool.append(rec(0, at=T0 + 86400))
    assert spool.prune(now=done.stat().st_mtime + 60) == 0
    assert spool.prune(now=other.stat().st_mtime + 10 * spool.DONE_KEEP_S) == 1  # only `done` is done
    assert [p.name for p in spool.spool_files()] == [other.name]


# --- locks ------------------------------------------------------------------------------------------------------


def test_a_lock_is_exclusive_and_released_on_unlock():
    path = paths.data_root() / "capture" / "x.lock"
    assert not spool.lock_held(path)  # no file yet
    fd = spool.try_lock(path)
    assert fd is not None
    assert spool.try_lock(path) is None and spool.lock_held(path)
    spool.unlock(fd)
    assert not spool.lock_held(path)
    fd = spool.try_lock(path)
    assert fd is not None
    spool.unlock(fd)


# --- scrubbing --------------------------------------------------------------------------------------------------


def test_the_scrubber_replaces_a_secret_and_the_function_returns_text():
    fn, name = spool.load_scrubber()
    assert name == "secrets"
    out = fn(f"use {FAKE_TOKEN} for the push")
    assert FAKE_TOKEN not in out and out.startswith("use ") and out.endswith(" for the push")
    assert fn(out) == out  # a second pass changes nothing


def test_scrub_value_reaches_every_string_however_deep():
    got = spool.scrub_value({"a": "x", "b": ["y", {"c": "z", "n": 3, "t": True}], "d": None}, str.upper)
    assert got == {"a": "X", "b": ["Y", {"c": "Z", "n": 3, "t": True}], "d": None}


def _break_the_scrubber(monkeypatch):
    monkeypatch.setitem(sys.modules, "northstar_agent_memory.capture.secrets", None)  # an import now fails


def test_without_the_scrubber_a_test_run_gets_a_no_op_named_as_such(monkeypatch):
    _break_the_scrubber(monkeypatch)
    fn, name = spool.load_scrubber()
    assert name == "noop" and fn(FAKE_TOKEN) == FAKE_TOKEN


def test_without_the_scrubber_a_real_run_gets_nothing(monkeypatch):
    _break_the_scrubber(monkeypatch)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("NORTHSTAR_TEST_MODE", raising=False)
    assert spool.load_scrubber() is None
    monkeypatch.setenv("NORTHSTAR_TEST_MODE", "1")
    assert spool.load_scrubber()[1] == "noop"


# --- the capture log --------------------------------------------------------------------------------------------


def test_the_log_gets_one_line_per_call():
    spool.log("hook", "ValueError: bad thing\nwith a second line")
    spool.log("ingest", "all fine", level="info")
    lines = spool.log_path().read_text().splitlines()
    assert len(lines) == 2
    assert " error hook " in lines[0] and "ValueError: bad thing with a second line" in lines[0]
    assert " info ingest " in lines[1]
    assert stat.S_IMODE(spool.log_path().stat().st_mode) == 0o600


def test_the_log_never_raises(tmp_path):
    blocker = tmp_path / "a-file"
    blocker.write_text("x")
    spool.log("hook", "cannot be written", root=blocker)  # the root is a file: the folder cannot be made


def test_the_log_rotates_when_large(monkeypatch):
    monkeypatch.setattr(spool, "LOG_LIMIT_BYTES", 200)
    for i in range(10):
        spool.log("hook", f"line {i} " + "x" * 50)
    assert spool.log_path().with_name("capture.log.1").exists()
    assert spool.log_path().stat().st_size < 600


def test_the_spool_and_log_stay_under_the_data_root():
    spool.append(rec(0))
    spool.log("hook", "x")
    root = paths.data_root()
    for p in (spool.spool_dir(), spool.capture_dir(), spool.lock_path(), spool.state_path()):
        assert Path(p).is_relative_to(root)


# --- owner-only folders, parents included -----------------------------------------------------------------------


@pytest.fixture
def open_umask():
    """A umask that hides nothing, so a folder is only owner-only if the code says so."""
    old = os.umask(0)
    yield
    os.umask(old)


def modes(*folders: Path) -> list[int]:
    return [stat.S_IMODE(f.stat().st_mode) for f in folders]


def test_the_folders_above_the_spool_are_made_owner_only_too(tmp_path, open_umask):
    root = tmp_path / "fresh" / "Application Support" / "Northstar"  # none of it exists: makedirs(mode=) would leave 0777 parents
    spool.append(rec(), root=root)
    base = tmp_path / "fresh"
    assert modes(base, base / "Application Support", root, root / "spool", root / "spool" / "claude-code") == [0o700] * 5
    assert stat.S_IMODE(spool.spool_files(root)[0].stat().st_mode) == 0o600


def test_the_log_and_the_lock_make_owner_only_parents_too(tmp_path, open_umask):
    root = tmp_path / "fresh" / "Northstar"
    spool.log("hook", "x", root=root)
    assert modes(tmp_path / "fresh", root, root / "capture") == [0o700] * 3
    other = tmp_path / "second" / "Northstar"
    fd = spool.try_lock(spool.lock_path(other))
    spool.unlock(fd)
    assert modes(tmp_path / "second", other, other / "capture") == [0o700] * 3


def test_a_folder_that_exists_is_left_as_it_is(tmp_path, open_umask):
    root = tmp_path / "Northstar"
    root.mkdir(mode=0o755)
    spool.append(rec(), root=root)
    assert modes(root) == [0o755] and modes(root / "spool") == [0o700]  # only what was made here is made private


def test_two_hooks_making_the_same_folders_at_once_do_not_fail(tmp_path):
    errors = []

    def go(n):
        try:
            spool.append(rec(n), root=tmp_path / "Northstar")
        except Exception as err:  # pragma: no cover - the failure is the point
            errors.append(err)

    threads = [threading.Thread(target=go, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [] and len(spool.read_pending(tmp_path / "Northstar")) == 8


# --- markers ----------------------------------------------------------------------------------------------------


def test_a_marker_holds_no_text_and_reads_back_as_a_record_of_the_event():
    marker = spool.make_marker(
        "UserPromptSubmit", SESSION, {"prompt": 1234}, transcript_path="/nowhere/t.jsonl", cwd="/x", now=T0)
    assert (marker["event"], marker["session_id"], marker["transcript_path"], marker["cwd"]) == (
        "UserPromptSubmit", SESSION, "/nowhere/t.jsonl", "/x")
    assert marker["scrub"] == spool.MARKER_SCRUB and marker["payload"] == {"marker": "scrub_pending", "sizes": {"prompt": 1234}}
    assert spool.is_marker(marker) and not spool.is_marker(rec())
    spool.append(marker)
    (read,) = spool.read_pending()
    assert spool.is_marker(read) and read.session_id == SESSION and read.transcript_path == "/nowhere/t.jsonl"


def test_an_append_without_sync_is_still_in_the_file_and_the_default_syncs(monkeypatch):
    synced = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (synced.append(fd), real(fd)))
    spool.append(rec(0), sync=False)
    assert synced == [] and len(spool.read_pending()) == 1
    spool.append(rec(1))
    assert len(synced) == 1 and len(spool.read_pending()) == 2


# --- the encryption stamp ---------------------------------------------------------------------------------------


def test_there_is_no_stamp_until_one_is_written_and_then_it_is_valid():
    ok, why = spool.encryption_stamp()
    assert not ok and "no encryption stamp" in why and "northstar capture install" in why
    path = spool.write_encryption_stamp(now=T0)
    assert path == spool.stamp_path() == paths.data_root() / "capture" / "encryption.stamp"
    ok, why = spool.encryption_stamp()
    assert ok and "2026-03-02T09:00:00.000Z" in why
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    data = json.loads(path.read_text())
    assert data["v"] == 1 and data["data_root"] == os.path.realpath(paths.data_root()) and data["device"] == paths.data_root().stat().st_dev


def test_a_stamp_is_for_one_data_root_and_one_volume(tmp_path):
    spool.write_encryption_stamp()
    stamp = spool.stamp_path().read_text()
    other = tmp_path / "other-root"
    (other / "capture").mkdir(parents=True)
    (other / "capture" / "encryption.stamp").write_text(stamp)  # copied from the root it was written for
    ok, why = spool.encryption_stamp(other)
    assert not ok and "another data folder" in why
    data = json.loads(stamp)
    data["device"] += 1
    spool.stamp_path().write_text(json.dumps(data))
    ok, why = spool.encryption_stamp()
    assert not ok and "another volume" in why


@pytest.mark.parametrize("text", ["", "{", "[]", '{"v": 2}', '{"v": 1}', "\x00"])
def test_a_damaged_stamp_is_invalid_not_an_error(text):
    spool.write_encryption_stamp()
    spool.stamp_path().write_text(text, encoding="ascii")
    ok, why = spool.encryption_stamp()
    assert not ok and why


def test_writing_a_stamp_again_replaces_it_and_leaves_no_temporary_file():
    spool.write_encryption_stamp(now=T0)
    spool.write_encryption_stamp(now=T0 + 60)
    assert "09:01:00" in spool.encryption_stamp()[1]
    assert sorted(p.name for p in spool.capture_dir().iterdir()) == ["encryption.stamp"]
