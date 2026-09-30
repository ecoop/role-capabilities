# Copyright (c) 2026 Eric Cooper.
"""Persistence for role overrides — an append-only log of role assignments.

Roles are resolved from two sources: a static *seed* (baseline, redeploy to
change) and *overrides* — an append-only log where the latest row for a principal
wins and a `reset` row falls back to the seed. This module is the log's storage
seam: a `RoleStore` reads all rows and appends one, nothing more. An app picks a
backend (in-memory for tests/dev, GCS or SQL in production) without the resolver
knowing which.

The row shape is a plain mapping: at least ``{"principal": <id>, "role": <id>}``,
optionally audit fields (``actor``, ``at``) written by the resolver. Keeping it a
plain append-only log makes the store trivial to back with a jsonl object or a
table, and keeps the whole assignment history auditable.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class RoleStore(Protocol):
    """A backend for the append-only role-override log.

    Two operations, deliberately minimal: read every row (oldest → newest) and
    append one. Replay (latest-wins, reset-clears) lives in the resolver, not the
    store, so every backend behaves identically.
    """

    def read_rows(self) -> list[dict]:
        """All rows in append order; an empty list when the log is absent/empty."""
        ...

    def append_row(self, row: Mapping[str, object]) -> None:
        """Append one row to the log."""
        ...


class MemoryRoleStore:
    """An in-process `RoleStore` — for tests, local dev, and examples.

    Not durable: rows live only for the object's lifetime. Copies rows in and out
    so a caller can't mutate the log through a returned reference.
    """

    def __init__(self, rows: Iterable[Mapping[str, object]] | None = None) -> None:
        self._rows: list[dict] = [dict(r) for r in (rows or [])]

    def read_rows(self) -> list[dict]:
        return [dict(r) for r in self._rows]

    def append_row(self, row: Mapping[str, object]) -> None:
        self._rows.append(dict(row))
