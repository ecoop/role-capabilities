# Copyright (c) 2026 Eric Cooper.
"""Replaying the append-only override log to effective role assignments.

The log is a sequence of rows; replaying it yields the current
``{principal: role}`` map. Rules (matching Rulebook's roles.jsonl semantics):

    - latest row for a principal wins,
    - a `reset` row clears the principal's override (it falls back to the seed),
    - a row naming an unknown role is ignored (fail closed on bad data), and
    - roles are canonicalized through the model's aliases on the way in.

The resolver that layers override ▸ seed ▸ default on top of this lands in the
next slice; this is the pure replay it will build on.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .capabilities import CapabilityModel

RESET_SENTINEL = "reset"
"""A row whose role is this value clears the principal's override."""


def replay_overrides(
    rows: Iterable[Mapping[str, object]], *, model: CapabilityModel
) -> dict[str, str]:
    """Replay append-only override rows to ``{principal: canonical_role}``.

    Rows are processed in order, so a later row for a principal supersedes an
    earlier one; a ``reset`` row removes the principal; a row naming an invalid
    role is skipped. ``principal`` and ``role`` are read from each row's fields of
    those names; a row missing a principal is skipped.
    """
    out: dict[str, str] = {}
    for row in rows:
        principal = str(row.get("principal", ""))
        role = str(row.get("role", ""))
        if not principal:
            continue
        if role == RESET_SENTINEL:
            out.pop(principal, None)
        elif model.is_valid_role(role):
            out[principal] = model.canonical_role(role)
    return out
