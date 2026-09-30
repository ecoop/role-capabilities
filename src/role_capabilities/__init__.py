# Copyright (c) 2026 Eric Cooper.
"""role-capabilities — app-agnostic, capability-based roles.

Declare your own closed set of capabilities and your own role → capability
bundles, then ask a `CapabilityModel` "may this role do X?". Nothing here carries
an application's vocabulary; the app injects its own names.

Extraction from Rulebook lands incrementally (see ecoop/rulebook#220). This core
module carries the framework-free engine: the capability model, role ordering,
resolution (override ▸ seed ▸ default, TTL-cached, audited) over a pluggable
`RoleStore` (in-memory + GCS), and the role-admin surface (change/reset plus
`assignments`/`roster`). Identity lifecycle (add/remove/rename a user) stays in
the app's identity layer, not here.

Optional adapters live in their own modules so importing this core needs no extra
dependency — `role_capabilities.fastapi_dep.make_require_capability` (needs the
`fastapi` extra) and `role_capabilities.guest_auth_adapter.guest_principal_provider`
(needs the `guest-auth` extra). Next: Rulebook adopts the library.
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
