# Copyright (c) 2026 Eric Cooper.
"""role-capabilities — app-agnostic, capability-based roles.

Declare your own closed set of capabilities and your own role → capability
bundles, then ask a `CapabilityModel` "may this role do X?". Nothing here carries
an application's vocabulary; the app injects its own names.

Extraction from Rulebook lands incrementally (see ecoop/rulebook#220). Shipped so
far: the capability engine, role ordering, and role resolution (override ▸ seed ▸
default, TTL-cached, audited) over a pluggable `RoleStore` with in-memory and GCS
backends. Still to come: user-admin operations and an optional FastAPI
`require_capability` + guest-auth adapter.
"""

from __future__ import annotations

from .capabilities import CapabilityModel, capability_fingerprint
from .resolution import RESET_SENTINEL, RoleResolver, replay_overrides
from .store import GcsRoleStore, MemoryRoleStore, RoleStore

__version__ = "0.0.1"

__all__ = [
    "RESET_SENTINEL",
    "CapabilityModel",
    "GcsRoleStore",
    "MemoryRoleStore",
    "RoleResolver",
    "RoleStore",
    "__version__",
    "capability_fingerprint",
    "replay_overrides",
]
