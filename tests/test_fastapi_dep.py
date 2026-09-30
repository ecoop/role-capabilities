# Copyright (c) 2026 Eric Cooper.
"""Tests for the FastAPI require_capability dependency (framework glue only)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from role_capabilities import CapabilityModel, MemoryRoleStore, RoleResolver
from role_capabilities.fastapi_dep import make_require_capability

CAPS = {"read", "write", "admin"}
ROLES = {
    "guest": frozenset(),
    "member": {"read", "write"},
    "owner": {"read", "write", "admin"},
}
MODEL = CapabilityModel(capabilities=CAPS, roles=ROLES, default_role="member")


def build(*, gate=None, public_role=None, principal="root"):
    resolver = RoleResolver(
        model=MODEL,
        store=MemoryRoleStore(),
        seed={"root": "owner", "m": "member"},
    )
    current = {"p": principal}
    require = make_require_capability(
        resolver,
        principal_provider=lambda: current["p"],
        gate_enabled=gate,
        public_role=public_role,
    )
    return require, current, resolver


def test_allows_when_role_has_capability():
    require, _, _ = build(principal="root")
    assert require("admin")() is None          # root → owner → has admin


def test_403_when_role_lacks_capability():
    require, _, _ = build(principal="m")
    with pytest.raises(HTTPException) as ei:
        require("admin")()
    assert ei.value.status_code == 403


def test_anonymous_principal_falls_to_default_role():
    require, _, _ = build(principal=None)       # None → default 'member'
    assert require("read")() is None            # member has read
    with pytest.raises(HTTPException):
        require("admin")()                      # member lacks admin


def test_gate_off_allows_only_the_public_tier():
    require, _, _ = build(gate=lambda: False, public_role="member")
    assert require("read")() is None            # public tier (member) has read
    with pytest.raises(HTTPException) as ei:
        require("admin")()                      # not in the public tier
    assert ei.value.status_code == 403


def test_gate_off_public_tier_defaults_to_model_default_role():
    require, _, _ = build(gate=lambda: False)   # public_role None → default 'member'
    assert require("write")() is None


def test_dependency_reflects_a_role_change():
    require, _, resolver = build(principal="m")
    with pytest.raises(HTTPException):
        require("admin")()
    resolver.set_role("m", "owner")
    assert require("admin")() is None
