# Copyright (c) 2026 Eric Cooper.
"""role-capabilities — app-agnostic, capability-based roles.

Scaffold only. The extraction from Rulebook lands incrementally; see the design
issue ecoop/rulebook#220 for the target API and scope. What ships here so far is
the package skeleton and its version, so the distribution builds and imports
cleanly on every supported interpreter.

The intended surface, once extracted:

    - a capability engine (app-injected capability set + role → bundle map),
    - role resolution (seed + append-only overrides, latest wins, reset → seed),
    - a RoleStore protocol (read_rows / append_row) with GCS and SQL backends,
    - has_capability(actor, capability) usable outside any web request, and
    - an optional FastAPI require_capability + a guest-auth actor adapter.
"""

from __future__ import annotations

__version__ = "0.0.1"

__all__ = ["__version__"]
