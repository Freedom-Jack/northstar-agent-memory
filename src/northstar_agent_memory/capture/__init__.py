"""Capture: what is said in the user's AI sessions goes into chat history at once (MEMORY-ARCHITECTURE §2.2, §5.2).

For Claude Code the pieces are:
- scope.py: the scope gate (only sessions inside a personal folder) and the self-capture guard (I24);
- hook.py: the entry point Claude Code runs for each hook event; it scrubs, spools and exits;
- spool.py: the append-only day files the hooks write, and the capture log;
- ingest.py: the one writer of history.db, which drains the spool and reconciles against the transcripts.

This package's start-up cost is the hook's start-up cost, so nothing is imported here.
"""
