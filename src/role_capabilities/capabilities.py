# Copyright (c) 2026 Eric Cooper.
"""The capability engine.

An app declares its own closed set of capabilities and its role → capability
bundles; this model answers "may this role do X?". Nothing here carries an
application's vocabulary — no `ask`, no `golds.*`. The app constructs a
`CapabilityModel` with its own names; the library only enforces the shape
(bundles stay within the closed set) and answers membership queries.

This is the *mechanism* half of the split the roadmap draws: capabilities decide
what a role may **do**. Ordering, presentation, resolution, and persistence are
separate concerns that land in later slices (see ecoop/rulebook#220).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping


def capability_fingerprint(caps: Iterable[str]) -> str:
    """Short, order-independent content-address of a capability SET.

    Sorts before hashing, so the same set always yields the same 8-hex digest
    regardless of how it was assembled. A fingerprint, not an identity: it
    changes whenever the set changes — for dedup / "did this role's powers
    change?" / audit, never as an assignment key.
    """
    canonical = ",".join(sorted(set(caps)))
    return hashlib.sha256(canonical.encode()).hexdigest()[:8]


class CapabilityModel:
    """An app's closed capability vocabulary plus its role → capability bundles.

    Construct once (at module scope) from the app's own names and pass it where
    authorization is checked. Construction validates the declaration and fails
    loud on a malformed one; queries fail closed — an unknown role has no
    capabilities.

    Args:
        capabilities: the complete, closed set of capability ids a role may hold.
        roles: role id → the capabilities that role is granted. Every capability
            named must be in ``capabilities``.
        default_role: the role an unknown / unseeded principal resolves to; must
            be a declared role. (Resolution itself lands in a later slice; the
            model records the policy so one authority owns it.)
        aliases: legacy or synonym role id → canonical role id, applied on every
            read so assignments stored under an old id survive a rename. Each
            target must be a declared role, and an alias id must not shadow one.
    """

    def __init__(
        self,
        *,
        capabilities: Iterable[str],
        roles: Mapping[str, Iterable[str]],
        default_role: str,
        aliases: Mapping[str, str] | None = None,
    ) -> None:
        self.capabilities: frozenset[str] = frozenset(capabilities)
        self.roles: dict[str, frozenset[str]] = {
            role: frozenset(caps) for role, caps in roles.items()
        }
        self.aliases: dict[str, str] = dict(aliases or {})
        self.default_role: str = default_role
        self._validate()

    def _validate(self) -> None:
        for role, caps in self.roles.items():
            unknown = caps - self.capabilities
            if unknown:
                raise ValueError(
                    f"role {role!r} grants capabilities outside the closed set: "
                    f"{sorted(unknown)}"
                )
        if self.default_role not in self.roles:
            raise ValueError(
                f"default_role {self.default_role!r} is not a declared role"
            )
        for alias, target in self.aliases.items():
            if target not in self.roles:
                raise ValueError(
                    f"alias {alias!r} -> {target!r}: target is not a declared role"
                )
            if alias in self.roles:
                raise ValueError(
                    f"alias {alias!r} shadows a declared role of the same id"
                )

    def canonical_role(self, role: str) -> str:
        """Map a legacy / synonym role id to its canonical id; pass others through."""
        return self.aliases.get(role, role)

    def is_valid_role(self, role: str) -> bool:
        """True if ``role`` (after alias resolution) is a declared role."""
        return self.canonical_role(role) in self.roles

    def capabilities_for(self, role: str) -> frozenset[str]:
        """The capability bundle for a role; empty for an unknown role (fail closed)."""
        return self.roles.get(self.canonical_role(role), frozenset())

    def has_capability(self, role: str, capability: str) -> bool:
        """True if ``role`` holds ``capability`` (unknown role → False)."""
        return capability in self.capabilities_for(role)

    def role_fingerprint(self, role: str) -> str:
        """Fingerprint of a role's current capability bundle (empty set hashes too)."""
        return capability_fingerprint(self.capabilities_for(role))
