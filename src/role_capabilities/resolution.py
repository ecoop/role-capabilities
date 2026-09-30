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

import time
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime

from .capabilities import CapabilityModel
from .store import RoleStore

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


class RoleResolver:
    """Resolve a principal's effective role: override ▸ seed ▸ default.

    Ties a `CapabilityModel` (the vocabulary), a `RoleStore` (the override log),
    and a static seed together. Reads of the override log are TTL-cached and
    survive a backend read failure (last-good is reused), so authorization never
    hard-fails on a transient store hiccup. Writes (`set_role` / `reset_role`)
    append an audited row and bust the cache so the change is visible at once.

    Everything is keyed by an app-supplied **principal id** (a string), and the
    core checks take that principal explicitly — so this works in a web request
    or a plain CLI / batch job, with no framework or request context. Mapping an
    identity (a token, a guest, a session) to its principal id is the caller's
    job (and the FastAPI/guest-auth adapter's, in a later slice).

    Args:
        model: the capability model (vocabulary, aliases, default role).
        store: the override-log backend.
        seed: static ``{principal: role}`` baseline; every role must be valid.
        ttl_seconds: how long a replayed override snapshot is cached.
        clock: monotonic time source (injectable for tests).
    """

    def __init__(
        self,
        *,
        model: CapabilityModel,
        store: RoleStore,
        seed: Mapping[str, str] | None = None,
        ttl_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._model = model
        self._store = store
        self._ttl = ttl_seconds
        self._clock = clock
        seed = seed or {}
        bad = sorted({r for r in seed.values() if not model.is_valid_role(r)})
        if bad:
            raise ValueError(f"seed assigns unknown roles: {bad}")
        self._seed: dict[str, str] = {
            principal: model.canonical_role(role) for principal, role in seed.items()
        }
        self._cache: tuple[float, dict[str, str]] | None = None

    # ── resolution ──────────────────────────────────────────────────────────

    def resolve(self, principal: str | None) -> str:
        """Effective role for a principal: override ▸ seed ▸ default."""
        if principal is None:
            return self._model.default_role
        overrides = self._effective_overrides()
        if principal in overrides:
            return overrides[principal]
        if principal in self._seed:
            return self._seed[principal]
        return self._model.default_role

    def capabilities_for(self, principal: str | None) -> frozenset[str]:
        """The capability bundle a principal effectively holds."""
        return self._model.capabilities_for(self.resolve(principal))

    def has_capability(self, principal: str | None, capability: str) -> bool:
        """True if the principal's effective role holds ``capability``."""
        return self._model.has_capability(self.resolve(principal), capability)

    def _effective_overrides(self) -> dict[str, str]:
        now = self._clock()
        if self._cache is not None and now < self._cache[0]:
            return self._cache[1]
        try:
            overrides = replay_overrides(self._store.read_rows(), model=self._model)
        except Exception:  # noqa: BLE001 — authz must survive a bad store read
            overrides = self._cache[1] if self._cache is not None else {}
        self._cache = (now + self._ttl, overrides)
        return overrides

    # ── mutation (audited) ────────────────────────────────────────────────────

    def set_role(self, principal: str, role: str, *, actor: str | None = None) -> None:
        """Assign ``role`` to ``principal`` — appends an audited override row."""
        if not self._model.is_valid_role(role):
            raise ValueError(f"unknown role {role!r}")
        self._store.append_row(
            self._audited(
                {"principal": principal, "role": self._model.canonical_role(role)},
                actor,
            )
        )
        self._cache = None

    def reset_role(self, principal: str, *, actor: str | None = None) -> None:
        """Clear ``principal``'s override so it falls back to the seed/default."""
        self._store.append_row(
            self._audited({"principal": principal, "role": RESET_SENTINEL}, actor)
        )
        self._cache = None

    def _audited(self, row: dict[str, object], actor: str | None) -> dict[str, object]:
        row = dict(row)
        row["at"] = datetime.now(UTC).isoformat()
        if actor is not None:
            row["actor"] = actor
        return row

    # ── roster (read) ─────────────────────────────────────────────────────────

    def assignments(self) -> dict[str, str]:
        """Every principal the system has an explicit opinion about → its role.

        Seed overlaid by current overrides (an override wins; a `reset` drops the
        override so the seed shows through). Principals with no seed entry and no
        override are absent — they resolve to the default and aren't listed here.
        Use this to show "users with an assigned role"; pass the app's full user
        list to `roster` instead to include everyone at the default.
        """
        return {**self._seed, **self._effective_overrides()}

    def roster(self, principals: Iterable[str]) -> dict[str, str]:
        """Resolve a role for each of ``principals`` (including those at default).

        The app supplies the full set of principals it knows (from its own
        identity/invite store — the roles library does not enumerate users), and
        this returns ``{principal: effective_role}`` for building an admin table.
        """
        overrides = self._effective_overrides()
        return {
            p: (overrides.get(p) or self._seed.get(p) or self._model.default_role)
            for p in principals
        }

    # ── bootstrap ─────────────────────────────────────────────────────────────

    def assert_seeded(self, role: str) -> None:
        """Raise unless some seeded principal holds ``role`` — a bootstrap guard.

        Call at startup with your top/superuser role so a deploy can't come up
        with no one able to administer it. Checks the seed only: overrides can't
        exist before someone is seeded to write them.
        """
        canonical = self._model.canonical_role(role)
        if canonical not in self._seed.values():
            raise RuntimeError(
                f"no seeded principal holds role {role!r}; refusing to bootstrap"
            )
