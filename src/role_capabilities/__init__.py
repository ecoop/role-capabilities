# Copyright (c) 2026 Eric Cooper.
"""role-capabilities — app-agnostic, capability-based roles.

Declare your own closed set of capabilities and your own role → capability
bundles, then ask a `CapabilityModel` "may this role do X?". Nothing here carries
an application's vocabulary; the app injects its own names.

Extraction from Rulebook lands incrementally (see ecoop/rulebook#220). Shipped so
far: the capability engine and role ordering. Still to come: resolution (seed +
append-only overrides), a pluggable RoleStore (GCS / SQL), user-admin operations,
and an optional FastAPI `require_capability` + guest-auth adapter.
"""

from __future__ import annotations

from .capabilities import CapabilityModel, capability_fingerprint

__version__ = "0.0.1"

__all__ = ["CapabilityModel", "__version__", "capability_fingerprint"]
