# Copyright (c) 2026 Eric Cooper.
"""Tests for the guest-auth principal provider (current guest → principal id)."""

from __future__ import annotations

import types

import role_capabilities.guest_auth_adapter as ga
from role_capabilities.guest_auth_adapter import guest_principal_provider

GUEST = types.SimpleNamespace(token="tok_123", recipient="Alice")


def test_provider_keys_by_token_by_default(monkeypatch):
    monkeypatch.setattr(ga, "get_current_guest", lambda: GUEST)
    assert guest_principal_provider()() == "tok_123"


def test_provider_returns_none_without_a_guest(monkeypatch):
    monkeypatch.setattr(ga, "get_current_guest", lambda: None)
    assert guest_principal_provider()() is None


def test_provider_honors_a_custom_principal_key(monkeypatch):
    # key by a stable id so a rotated token doesn't drop the role
    monkeypatch.setattr(ga, "get_current_guest", lambda: GUEST)
    assert guest_principal_provider(lambda g: g.recipient)() == "Alice"
