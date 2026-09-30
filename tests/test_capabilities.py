# Copyright (c) 2026 Eric Cooper.
"""Tests for the capability engine — the mechanism, with a synthetic vocabulary.

Deliberately app-agnostic: a tiny made-up capability set, not Rulebook's, so
these pin the engine's behaviour rather than any one app's policy. (Rulebook's
own rung boundaries stay in Rulebook's suite, asserted against a model it builds
from its declarations.)
"""

from __future__ import annotations

import pytest

from role_capabilities import CapabilityModel, capability_fingerprint

# A small closed vocabulary and a three-role ladder over it.
CAPS = {"read", "write", "admin"}
ROLES = {
    "guest": frozenset(),
    "member": {"read", "write"},
    "owner": {"read", "write", "admin"},
}


def model(**over) -> CapabilityModel:
    kw = {"capabilities": CAPS, "roles": ROLES, "default_role": "member"}
    kw.update(over)
    return CapabilityModel(**kw)


# ── queries ──────────────────────────────────────────────────────────────────


def test_has_capability_and_bundles():
    m = model()
    assert m.has_capability("member", "read")
    assert m.has_capability("owner", "admin")
    assert not m.has_capability("member", "admin")
    assert m.capabilities_for("owner") == frozenset(CAPS)
    assert m.capabilities_for("guest") == frozenset()


def test_unknown_role_fails_closed():
    m = model()
    assert m.capabilities_for("wizard") == frozenset()
    assert not m.has_capability("wizard", "read")
    assert not m.is_valid_role("wizard")


def test_is_valid_role():
    m = model()
    assert m.is_valid_role("owner")
    assert not m.is_valid_role("nope")


# ── aliases ──────────────────────────────────────────────────────────────────


def test_aliases_resolve_on_every_read():
    m = model(aliases={"legacy_admin": "owner", "level1": "member"})
    assert m.canonical_role("legacy_admin") == "owner"
    assert m.canonical_role("owner") == "owner"          # already canonical
    assert m.canonical_role("unknown") == "unknown"      # passes through
    # validity / caps honour the alias
    assert m.is_valid_role("legacy_admin")
    assert m.has_capability("level1", "write")
    assert m.capabilities_for("legacy_admin") == m.capabilities_for("owner")


# ── fingerprints ─────────────────────────────────────────────────────────────


def test_capability_fingerprint_is_order_independent():
    assert capability_fingerprint(["read", "write"]) == capability_fingerprint(
        ["write", "read"]
    )
    assert len(capability_fingerprint(["read"])) == 8


def test_fingerprint_changes_with_the_set():
    assert capability_fingerprint(["read"]) != capability_fingerprint(
        ["read", "write"]
    )


def test_role_fingerprint_tracks_the_bundle():
    m = model()
    assert m.role_fingerprint("member") == capability_fingerprint({"read", "write"})
    assert m.role_fingerprint("member") != m.role_fingerprint("owner")


# ── construction validation (fail loud on a bad declaration) ──────────────────


def test_bundle_outside_closed_set_is_rejected():
    with pytest.raises(ValueError, match="outside the closed set"):
        CapabilityModel(
            capabilities={"read"},
            roles={"member": {"read", "delete"}},
            default_role="member",
        )


def test_bad_default_role_is_rejected():
    with pytest.raises(ValueError, match="default_role"):
        CapabilityModel(capabilities=CAPS, roles=ROLES, default_role="nope")


def test_alias_to_unknown_target_is_rejected():
    with pytest.raises(ValueError, match="target is not a declared role"):
        model(aliases={"old": "ghost"})


def test_alias_shadowing_a_real_role_is_rejected():
    with pytest.raises(ValueError, match="shadows a declared role"):
        model(aliases={"owner": "member"})
