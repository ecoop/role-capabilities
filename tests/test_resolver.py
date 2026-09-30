# Copyright (c) 2026 Eric Cooper.
"""Tests for RoleResolver — override ▸ seed ▸ default, TTL caching, audited writes."""

from __future__ import annotations

import pytest

from role_capabilities import (
    CapabilityModel,
    GcsRoleStore,
    MemoryRoleStore,
    RoleResolver,
    RoleStore,
)

CAPS = {"read", "write", "admin"}
ROLES = {
    "guest": frozenset(),
    "member": {"read", "write"},
    "owner": {"read", "write", "admin"},
}
MODEL = CapabilityModel(
    capabilities=CAPS,
    roles=ROLES,
    default_role="member",
    aliases={"legacy_admin": "owner"},
)


def resolver(**over) -> RoleResolver:
    kw = {"model": MODEL, "store": MemoryRoleStore(), "seed": {"root": "owner"}}
    kw.update(over)
    return RoleResolver(**kw)


# ── resolution order ───────────────────────────────────────────────────────────


def test_resolve_override_then_seed_then_default():
    r = resolver()
    assert r.resolve("root") == "owner"        # seed
    assert r.resolve("nobody") == "member"     # default
    assert r.resolve(None) == "member"         # anonymous → default
    r.set_role("root", "guest")                # override beats seed
    assert r.resolve("root") == "guest"


def test_capability_helpers_resolve_then_check():
    r = resolver(seed={"root": "owner", "m": "member"})
    assert r.has_capability("root", "admin")
    assert not r.has_capability("m", "admin")
    assert r.has_capability("m", "write")
    assert r.capabilities_for("m") == frozenset({"read", "write"})
    assert r.capabilities_for("nobody") == r._model.capabilities_for("member")


# ── audited writes ─────────────────────────────────────────────────────────────


def test_set_role_writes_canonical_audited_row():
    store = MemoryRoleStore()
    r = resolver(store=store)
    r.set_role("u", "legacy_admin", actor="admin@x")   # alias in, canonical stored
    row = store.read_rows()[-1]
    assert row["principal"] == "u"
    assert row["role"] == "owner"
    assert row["actor"] == "admin@x"
    assert "at" in row                                  # timestamp recorded
    assert r.resolve("u") == "owner"


def test_reset_role_falls_back_to_seed():
    r = resolver()
    r.set_role("root", "guest")
    assert r.resolve("root") == "guest"
    r.reset_role("root", actor="admin@x")
    assert r.resolve("root") == "owner"                 # back to the seed


def test_set_unknown_role_is_rejected():
    r = resolver()
    with pytest.raises(ValueError, match="unknown role"):
        r.set_role("u", "wizard")


# ── seed validation & bootstrap ─────────────────────────────────────────────────


def test_seed_with_unknown_role_is_rejected():
    with pytest.raises(ValueError, match="seed assigns unknown roles"):
        RoleResolver(model=MODEL, store=MemoryRoleStore(), seed={"x": "wizard"})


def test_assert_seeded_guards_bootstrap():
    RoleResolver(
        model=MODEL, store=MemoryRoleStore(), seed={"root": "owner"}
    ).assert_seeded("owner")  # ok
    with pytest.raises(RuntimeError, match="refusing to bootstrap"):
        RoleResolver(
            model=MODEL, store=MemoryRoleStore(), seed={"x": "member"}
        ).assert_seeded("owner")


# ── TTL caching ────────────────────────────────────────────────────────────────


def test_overrides_are_ttl_cached_but_writes_bust_the_cache():
    clock = {"t": 100.0}
    store = MemoryRoleStore()
    r = resolver(store=store, ttl_seconds=30.0, clock=lambda: clock["t"])

    assert r.resolve("u") == "member"                   # caches empty overrides
    store.append_row({"principal": "u", "role": "owner"})  # written behind the cache
    assert r.resolve("u") == "member"                   # still cached
    clock["t"] = 131.0                                  # TTL expired
    assert r.resolve("u") == "owner"                    # re-read

    # a write through the resolver is visible immediately, no clock advance
    r.set_role("u", "guest")
    assert r.resolve("u") == "guest"


def test_read_failure_reuses_last_good():
    class FlakyStore:
        def __init__(self):
            self.calls = 0
            self.rows = [{"principal": "u", "role": "owner"}]

        def read_rows(self):
            self.calls += 1
            if self.calls == 1:
                return list(self.rows)
            raise RuntimeError("backend down")

        def append_row(self, row):  # pragma: no cover - unused here
            self.rows.append(dict(row))

    clock = {"t": 0.0}
    r = RoleResolver(
        model=MODEL, store=FlakyStore(), seed={}, ttl_seconds=1.0,
        clock=lambda: clock["t"],
    )
    assert r.resolve("u") == "owner"     # first read succeeds, cached
    clock["t"] = 5.0                     # expire; next read raises
    assert r.resolve("u") == "owner"     # last-good reused, no crash


# ── GCS backend (structural — no live GCS in CI) ────────────────────────────────


def test_gcs_store_is_a_rolestore_and_construction_is_lazy():
    # Constructing must not require google-cloud (the import is inside the methods).
    store = GcsRoleStore("some-bucket", "roles.jsonl")
    assert isinstance(store, RoleStore)
    assert store.bucket == "some-bucket"
