# Copyright (c) 2026 Eric Cooper.
"""Tests for the role-admin read surface — assignments() and roster()."""

from __future__ import annotations

from role_capabilities import CapabilityModel, MemoryRoleStore, RoleResolver

CAPS = {"read", "write", "admin"}
ROLES = {
    "guest": frozenset(),
    "member": {"read", "write"},
    "owner": {"read", "write", "admin"},
}
MODEL = CapabilityModel(capabilities=CAPS, roles=ROLES, default_role="member")


def resolver(**over) -> RoleResolver:
    kw = {"model": MODEL, "store": MemoryRoleStore(), "seed": {"root": "owner"}}
    kw.update(over)
    return RoleResolver(**kw)


def test_assignments_merges_seed_and_overrides():
    r = resolver(seed={"root": "owner", "carol": "member"})
    r.set_role("dave", "guest")            # override for a non-seeded principal
    r.set_role("carol", "owner")           # override wins over seed
    assert r.assignments() == {
        "root": "owner",     # seed, untouched
        "carol": "owner",    # override beats seed
        "dave": "guest",     # override-only
    }


def test_assignments_reset_drops_override_back_to_seed():
    r = resolver(seed={"root": "owner"})
    r.set_role("root", "guest")
    assert r.assignments()["root"] == "guest"
    r.reset_role("root")
    assert r.assignments()["root"] == "owner"        # seed shows through again


def test_assignments_excludes_pure_default_principals():
    r = resolver(seed={"root": "owner"})
    # "nobody" has neither seed nor override → not listed (resolves to default)
    assert "nobody" not in r.assignments()


def test_roster_includes_defaults_for_supplied_principals():
    r = resolver(seed={"root": "owner"})
    r.set_role("dave", "guest")
    roster = r.roster(["root", "dave", "erin"])
    assert roster == {
        "root": "owner",     # seed
        "dave": "guest",     # override
        "erin": "member",    # default (no seed, no override)
    }


def test_roster_empty_input():
    assert resolver().roster([]) == {}
