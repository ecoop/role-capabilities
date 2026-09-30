# Copyright (c) 2026 Eric Cooper.
"""Tests for the presentational role ladder — order, ordered_roles, role_order.

Ordering is a display/sort axis only; no authorization reads it. These pin that
the ladder can be declared explicitly or fall out of declaration order, and that
it stays a permutation of the declared roles.
"""

from __future__ import annotations

import pytest

from role_capabilities import CapabilityModel

CAPS = {"read", "write", "admin"}
ROLES = {
    "guest": frozenset(),
    "member": {"read", "write"},
    "owner": {"read", "write", "admin"},
}


def test_ordering_defaults_to_declaration_order():
    m = CapabilityModel(capabilities=CAPS, roles=ROLES, default_role="member")
    assert m.ordered_roles() == ("guest", "member", "owner")
    assert m.role_order("guest") == 0
    assert m.role_order("owner") == 2


def test_explicit_order_overrides_declaration_order():
    # roles declared in a different order than the intended ladder
    roles = {"owner": {"read", "write", "admin"}, "guest": frozenset(), "member": {"read", "write"}}
    m = CapabilityModel(
        capabilities=CAPS,
        roles=roles,
        default_role="member",
        order=["guest", "member", "owner"],
    )
    assert m.ordered_roles() == ("guest", "member", "owner")
    assert m.role_order("member") == 1


def test_role_order_is_alias_aware():
    m = CapabilityModel(
        capabilities=CAPS,
        roles=ROLES,
        default_role="member",
        aliases={"legacy_admin": "owner"},
    )
    assert m.role_order("legacy_admin") == m.role_order("owner") == 2


def test_unranked_role_is_minus_one():
    m = CapabilityModel(capabilities=CAPS, roles=ROLES, default_role="member")
    # -1, not 0, so an unknown role is distinct from the bottom of the ladder
    assert m.role_order("wizard") == -1
    assert m.role_order("guest") == 0


def test_order_must_cover_exactly_the_roles():
    with pytest.raises(ValueError, match="permutation of the declared roles"):
        CapabilityModel(
            capabilities=CAPS, roles=ROLES, default_role="member",
            order=["guest", "member"],  # missing 'owner'
        )
    with pytest.raises(ValueError, match="permutation of the declared roles"):
        CapabilityModel(
            capabilities=CAPS, roles=ROLES, default_role="member",
            order=["guest", "member", "owner", "root"],  # unknown 'root'
        )


def test_order_rejects_duplicates():
    with pytest.raises(ValueError, match="duplicate role ids"):
        CapabilityModel(
            capabilities=CAPS, roles=ROLES, default_role="member",
            order=["guest", "member", "member"],
        )
