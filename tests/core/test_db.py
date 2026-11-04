"""Store files, PRAGMAs, migrations, transactions, encryption check and blob paths (MEMORY-ARCHITECTURE §3.1)."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from northstar_agent_memory import paths
from northstar_agent_memory.core import db


def pragma(conn, name):
    return conn.execute(f"PRAGMA {name}").fetchone()[0]


def test_there_are_six_stores():
    assert db.STORES == ("history", "memory", "working", "index", "overview", "runs")


def test_open_store_makes_the_file_under_the_root(store_root):
    conn = db.open_store("history", store_root)
    assert (store_root / "history.db").is_file()
    assert db.store_path("history", store_root) == store_root / "history.db"
    conn.close()


def test_open_store_uses_the_data_root_by_default(isolated_home):
    conn = db.open_store("working")
    assert (paths.data_root() / "working.db").is_file()
    assert paths.data_root().is_relative_to(isolated_home)
    conn.close()


def test_unknown_store_is_refused(store_root):
    with pytest.raises(ValueError):
        db.open_store("book", store_root)


@pytest.mark.parametrize("name", db.STORES)
def test_every_pragma_is_set(store_root, name):
    conn = db.open_store(name, store_root)
    assert pragma(conn, "journal_mode") == "wal"
    assert pragma(conn, "synchronous") == (2 if name in ("history", "memory", "working", "runs") else 1)
    assert pragma(conn, "secure_delete") == 1
    assert pragma(conn, "foreign_keys") == 1
    assert pragma(conn, "busy_timeout") == 5000
    conn.close()


def test_rows_come_back_by_column_name(history):
    row = history.execute("SELECT store, version FROM schema_version").fetchone()
    assert row["store"] == "history" and row["version"] == 1


@pytest.mark.parametrize("name", db.STORES)
def test_migrations_apply_once_and_are_recorded(store_root, name):
    conn = db.open_store(name, store_root)
    rows = conn.execute("SELECT store, version, applied_at, tenant_id FROM schema_version").fetchall()
    assert [(r["store"], r["version"], r["tenant_id"]) for r in rows] == [(name, 1, "local")]
    assert rows[0]["applied_at"].endswith("Z")
    assert db.migrate(conn, name) == []  # nothing is re-applied
    conn.close()
    again = db.open_store(name, store_root)  # reopening re-applies nothing either
    assert again.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1
    again.close()


def test_two_connections_to_one_store_work(store_root):
    a = db.open_store("memory", store_root)
    b = db.open_store("memory", store_root)
    assert pragma(b, "foreign_keys") == 1
    a.close()
    b.close()


@pytest.fixture
def schema_copy(tmp_path, monkeypatch):
    target = tmp_path / "schema"
    shutil.copytree(db.SCHEMA_DIR, target)
    monkeypatch.setattr(db, "SCHEMA_DIR", target)
    return target


def test_a_later_schema_file_is_applied_once(store_root, schema_copy):
    conn = db.open_store("history", store_root)
    assert db.current_version(conn, "history") == 1
    conn.close()
    (schema_copy / "history.2.sql").write_text(
        "-- a second version\nCREATE TABLE note (tenant_id TEXT NOT NULL DEFAULT 'local', id TEXT PRIMARY KEY);\n"
        "CREATE TRIGGER note_guard BEFORE DELETE ON note BEGIN SELECT RAISE(ABORT, 'no'); END;\n"
    )
    conn = db.open_store("history", store_root)
    assert db.current_version(conn, "history") == 2
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='note_guard'").fetchone()
    conn.close()
    conn = db.open_store("history", store_root)  # would fail on CREATE TABLE if it ran again
    assert [r[0] for r in conn.execute("SELECT version FROM schema_version ORDER BY version")] == [1, 2]
    conn.close()


def test_a_failing_migration_rolls_back_and_is_not_recorded(store_root, schema_copy):
    db.open_store("history", store_root).close()
    (schema_copy / "history.2.sql").write_text("CREATE TABLE half (id TEXT);\nCREATE TABLE half (id TEXT);\n")
    with pytest.raises(sqlite3.OperationalError):
        db.open_store("history", store_root)
    (schema_copy / "history.2.sql").unlink()
    conn = db.open_store("history", store_root)
    assert db.current_version(conn, "history") == 1
    assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='half'").fetchone()
    conn.close()


def test_schema_files_need_consecutive_versions(schema_copy):
    (schema_copy / "history.3.sql").write_text("SELECT 1;")
    with pytest.raises(RuntimeError, match="without gaps"):
        db.migration_files("history")


def test_a_schema_file_is_version_one_and_numbered_files_follow(schema_copy):
    (schema_copy / "memory.2.sql").write_text("SELECT 1;")
    files = db.migration_files("memory")
    assert [v for v, _ in files] == [1, 2]
    assert files[0][1].name == "memory.sql" and files[1][1].name == "memory.2.sql"
    assert [v for v, _ in db.migration_files("history")] == [1]  # memory.* does not leak into history


def test_statements_keeps_trigger_bodies_whole():
    script = "-- c\nCREATE TABLE t (a);\nCREATE TRIGGER g BEFORE DELETE ON t BEGIN SELECT RAISE(ABORT, 'x'); SELECT 1; END;\n-- end\n"
    parts = list(db.statements(script))
    assert len(parts) == 2 and "SELECT 1; END;" in parts[1]
    with pytest.raises(ValueError):
        list(db.statements("CREATE TABLE broken ("))


def test_transaction_commits(history):
    with db.transaction(history):
        history.execute(
            "INSERT INTO source (id, kind, scope, created_at) VALUES ('s1', 'chat', 'personal', 'now')"
        )
    assert not history.in_transaction
    assert history.execute("SELECT COUNT(*) FROM source").fetchone()[0] == 1


def test_transaction_rolls_back_on_error(history):
    with pytest.raises(RuntimeError, match="boom"):
        with db.transaction(history):
            history.execute("INSERT INTO source (id, kind, scope, created_at) VALUES ('s1', 'chat', 'personal', 'now')")
            raise RuntimeError("boom")
    assert not history.in_transaction
    assert history.execute("SELECT COUNT(*) FROM source").fetchone()[0] == 0


def test_transaction_rolls_back_on_a_constraint_error(history):
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction(history):
            history.execute("INSERT INTO source (id, kind, scope, created_at) VALUES ('s1', 'chat', 'personal', 'now')")
            history.execute("INSERT INTO source (id, kind, scope, created_at) VALUES ('s2', 'novel', 'personal', 'now')")
    assert history.execute("SELECT COUNT(*) FROM source").fetchone()[0] == 0


def test_transactions_do_not_nest(history):
    with db.transaction(history):
        with pytest.raises(RuntimeError, match="already"):
            with db.transaction(history):
                pass


def test_a_second_writer_waits_then_fails_with_busy(store_root):
    a = db.open_store("runs", store_root)
    b = db.open_store("runs", store_root)
    b.execute("PRAGMA busy_timeout=50")
    with db.transaction(a):
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            b.execute("BEGIN IMMEDIATE")
    a.close()
    b.close()


# --- encryption at rest (PL-3) ------------------------------------------------------------------------------------


def volume(**fields):
    """What `diskutil info` says about a volume, as `_volume_info` returns it."""
    return {"FileVault": False, "Locked": False, "MountPoint": "/Volumes/Plain", **fields}


@pytest.fixture
def real_root(monkeypatch, tmp_path):
    """A real data root: macOS, NORTHSTAR_HOME not set, the program lookups faked (none may run for real)."""
    monkeypatch.delenv("NORTHSTAR_HOME")
    monkeypatch.delenv(db.TEST_MARKER, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(db, "_fdesetup_status", lambda: "FileVault is Off.\n")
    monkeypatch.setattr(db, "_volume_info", lambda path: volume())
    return tmp_path


def test_encryption_is_skipped_under_a_temporary_northstar_home(monkeypatch):
    def refuse(*args):
        raise AssertionError("no program may run for a data root in a temporary folder")

    monkeypatch.setattr(db, "_fdesetup_status", refuse)
    monkeypatch.setattr(db, "_volume_info", refuse)
    db.require_encryption()


def test_northstar_home_outside_a_temporary_folder_does_not_skip_the_check(monkeypatch, real_root):
    """The attack: any NORTHSTAR_HOME at all switched the encryption check off, so real data went to a plain disk."""
    monkeypatch.setenv("NORTHSTAR_HOME", str(Path.home() / "northstar-dev"))
    with pytest.raises(db.EncryptionRequired, match="not on an encrypted volume"):
        db.require_encryption()
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(FileVault=True))
    db.require_encryption()


def test_a_link_inside_a_temporary_folder_does_not_make_a_real_root_temporary(monkeypatch, real_root):
    link = real_root / "link"
    link.symlink_to(Path.home())
    monkeypatch.setenv("NORTHSTAR_HOME", str(link))
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()


def test_the_test_marker_skips_the_check(monkeypatch, real_root):
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()
    for off in ("", "0"):
        monkeypatch.setenv(db.TEST_MARKER, off)
        with pytest.raises(db.EncryptionRequired):
            db.require_encryption()
    monkeypatch.setenv(db.TEST_MARKER, "1")
    db.require_encryption()


def test_a_real_root_needs_an_encrypted_volume(monkeypatch, real_root):
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(FileVault=True, MountPoint="/System/Volumes/Data"))
    db.require_encryption()  # FileVault on the boot volume
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(FileVault=True, MountPoint="/Volumes/Vault"))
    db.require_encryption()  # an encrypted disk image mounted for the data root


def test_a_locked_volume_does_not_count(monkeypatch, real_root):
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(FileVault=True, Locked=True))
    with pytest.raises(db.EncryptionRequired, match="locked"):
        db.require_encryption()


def test_filevault_on_does_not_cover_another_volume(monkeypatch, real_root):
    """FileVault encrypts the boot volume: a data root on an external plain disk is not covered by it."""
    monkeypatch.setattr(db, "_fdesetup_status", lambda: "FileVault is On.\n")
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(MountPoint="/Volumes/External"))
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(MountPoint="/System/Volumes/Data"))
    db.require_encryption()  # the boot volume, with FileVault on
    monkeypatch.setattr(db, "_fdesetup_status", lambda: "FileVault is Off.\n")
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()


def test_the_check_is_made_for_the_given_root(monkeypatch, real_root):
    asked = []
    monkeypatch.setattr(db, "_volume_info", lambda path: asked.append(path) or volume(FileVault=True))
    db.require_encryption(real_root / "elsewhere")
    assert asked == [real_root / "elsewhere"]


def test_encryption_check_failing_to_run_is_a_refusal(monkeypatch, real_root):
    def fail(path):
        raise subprocess.TimeoutExpired("diskutil", 10)

    monkeypatch.setattr(db, "_volume_info", fail)
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()
    monkeypatch.setattr(db, "_volume_info", lambda path: (_ for _ in ()).throw(FileNotFoundError("diskutil")))
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()
    monkeypatch.setattr(db, "_volume_info", lambda path: (_ for _ in ()).throw(ValueError("no such volume")))
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()
    monkeypatch.setattr(db, "_volume_info", lambda path: volume(MountPoint="/"))
    monkeypatch.setattr(db, "_fdesetup_status", lambda: (_ for _ in ()).throw(FileNotFoundError("fdesetup")))
    with pytest.raises(db.EncryptionRequired):
        db.require_encryption()


def test_encryption_is_left_to_the_platform_adapter_off_macos(monkeypatch, real_root):
    monkeypatch.setattr(sys, "platform", "win32")
    db.require_encryption()


def fake_run(outputs):
    """A stand-in for subprocess.run that answers by program name."""

    def run(argv, **kwargs):
        out, code = outputs[argv[0]]
        return subprocess.CompletedProcess(argv, code, stdout=out, stderr=b"")

    return run


def test_the_volume_is_found_with_df_then_described_by_diskutil(monkeypatch, tmp_path):
    import plistlib

    plist = plistlib.dumps({"FileVault": True, "MountPoint": "/Volumes/Vault", "Locked": False})
    seen = []

    def run(argv, **kwargs):
        seen.append(argv)
        if argv[0] == "df":
            return subprocess.CompletedProcess(argv, 0, stdout="Filesystem 512-blocks Used Available Capacity Mounted on\n/dev/disk9s1 10 5 5 50% /Volumes/Vault\n", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout=plist, stderr=b"")

    monkeypatch.setattr(subprocess, "run", run)
    target = tmp_path / "not" / "made" / "yet"  # the data root may not exist yet: its nearest folder is asked
    info = db._volume_info(target)
    assert info["FileVault"] is True and info["MountPoint"] == "/Volumes/Vault"
    assert seen[0] == ["df", "-P", str(tmp_path)]
    assert seen[1] == ["diskutil", "info", "-plist", "/dev/disk9s1"]


def test_a_volume_that_cannot_be_found_or_described_is_a_value_error(monkeypatch, tmp_path):
    import plistlib

    monkeypatch.setattr(subprocess, "run", fake_run({"df": ("Filesystem\nmap auto_home 0 0 0 100% /home\n", 0)}))
    with pytest.raises(ValueError, match="could not find the volume"):
        db._volume_info(tmp_path)
    monkeypatch.setattr(subprocess, "run", fake_run({"df": ("Filesystem\n/dev/disk9s1 1 1 0 100% /x\n", 1)}))
    with pytest.raises(ValueError, match="could not find the volume"):
        db._volume_info(tmp_path)
    error = plistlib.dumps({"Error": True, "ErrorMessage": "Could not find disk"})
    monkeypatch.setattr(subprocess, "run", fake_run({"df": ("Filesystem\n/dev/disk9s1 1 1 0 100% /x\n", 0), "diskutil": (error, 1)}))
    with pytest.raises(ValueError, match="Could not find disk"):
        db._volume_info(tmp_path)


def test_open_store_on_the_real_root_needs_encryption_and_makes_no_file_without_it(monkeypatch, isolated_home):
    def refuse():
        raise db.EncryptionRequired("off")

    monkeypatch.setattr(db, "require_encryption", refuse)
    with pytest.raises(db.EncryptionRequired):
        db.open_store("history")
    assert not (paths.data_root() / "history.db").exists()


def test_an_explicit_root_skips_the_encryption_check(monkeypatch, store_root):
    monkeypatch.setattr(db, "require_encryption", lambda: (_ for _ in ()).throw(AssertionError("not called")))
    db.open_store("history", store_root).close()


# --- blobs ----------------------------------------------------------------------------------------------------------


def test_blob_path_is_named_by_content_hash(store_root):
    sha = "ab" * 32
    assert db.blob_path(sha, store_root) == store_root / "blobs" / "ab" / "ab" / sha
    sha = "0123456789abcdef" * 4
    assert db.blob_path(sha, store_root) == store_root / "blobs" / "01" / "23" / sha


def test_blob_path_defaults_to_the_data_root():
    sha = "cd" * 32
    assert db.blob_path(sha) == paths.data_root() / "blobs" / "cd" / "cd" / sha


@pytest.mark.parametrize("bad", ["", "abc", "AB" * 32, "../" + "a" * 61, "g" * 64, "a" * 65])
def test_blob_path_refuses_anything_but_a_sha256_digest(bad):
    with pytest.raises(ValueError):
        db.blob_path(bad)


# --- starting values from the config (I19) ------------------------------------------------------------------------


def test_a_maintenance_setting_is_the_default_when_missing():
    assert db.maintenance_setting({}, "max_job_attempts", 3, whole=True, low=1) == 3
    assert db.maintenance_setting({"max_job_attempts": None}, "max_job_attempts", 3, whole=True, low=1) == 3
    assert db.maintenance_setting({"error_budget": 1}, "error_budget", 0.02, high=1) == 1.0
    assert isinstance(db.maintenance_setting({"x": 4.0}, "x", 1, whole=True), int)


@pytest.mark.parametrize(
    "kwargs, value",
    [
        (dict(whole=True), 1.5), (dict(), True), (dict(), "3"), (dict(low=1), 0), (dict(high=1), 1.5),
        (dict(low_open=True), 0), (dict(whole=True, low=1, high=3), 4),
    ],
)
def test_a_bad_maintenance_setting_is_refused_by_name(kwargs, value):
    with pytest.raises(ValueError, match=r"\[maintenance\] knob"):
        db.maintenance_setting({"knob": value}, "knob", 1, **kwargs)
