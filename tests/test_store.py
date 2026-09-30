# Copyright (c) 2026 Eric Cooper.
"""Tests for the override log: the in-memory store and append-only replay."""

from __future__ import annotations

from role_capabilities import (
    CapabilityModel,
    MemoryRoleStore,
    RoleStore,
    replay_overrides,
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


# ── MemoryRoleStore ────────────────────────────────────────────────────────────


def test_memory_store_reads_back_appended_rows_in_order():
    store = MemoryRoleStore()
    store.append_row({"principal": "a", "role": "owner"})
    store.append_row({"principal": "b", "role": "member"})
    assert store.read_rows() == [
        {"principal": "a", "role": "owner"},
        {"principal": "b", "role": "member"},
    ]


def test_memory_store_isolates_internal_state():
    store = MemoryRoleStore([{"principal": "a", "role": "owner"}])
    rows = store.read_rows()
    rows[0]["role"] = "guest"          # mutate the returned copy
    assert store.read_rows()[0]["role"] == "owner"   # log unchanged


def test_memory_store_satisfies_the_protocol():
    assert isinstance(MemoryRoleStore(), RoleStore)


# ── replay ─────────────────────────────────────────────────────────────────────


def test_replay_latest_wins_and_reset_clears():
    rows = [
        {"principal": "a", "role": "member"},
        {"principal": "a", "role": "owner"},    # supersedes
        {"principal": "b", "role": "owner"},
        {"principal": "b", "role": "reset"},    # cleared → falls back to seed
    ]
    assert replay_overrides(rows, model=MODEL) == {"a": "owner"}


def test_replay_skips_invalid_roles_and_principal_less_rows():
    rows = [
        {"principal": "a", "role": "bogus"},    # unknown role → ignored
        {"principal": "", "role": "owner"},     # no principal → ignored
        {"role": "owner"},                       # no principal → ignored
        {"principal": "c", "role": "member"},
    ]
    assert replay_overrides(rows, model=MODEL) == {"c": "member"}


def test_replay_canonicalizes_through_aliases():
    rows = [{"principal": "a", "role": "legacy_admin"}]
    assert replay_overrides(rows, model=MODEL) == {"a": "owner"}


def test_replay_reads_from_a_store():
    store = MemoryRoleStore(
        [
            {"principal": "a", "role": "member"},
            {"principal": "a", "role": "owner"},
        ]
    )
    assert replay_overrides(store.read_rows(), model=MODEL) == {"a": "owner"}


def test_replay_empty_is_empty():
    assert replay_overrides([], model=MODEL) == {}
