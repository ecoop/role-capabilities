# Copyright (c) 2026 Eric Cooper.
"""FastAPI dependency — gate an endpoint on a capability.

Optional: importing this module needs the ``fastapi`` extra
(``role-capabilities[fastapi]``). It is a thin layer over the framework-free core
— the resolver and model do the work; this only turns a failed check into an
HTTP 403 and reads the current principal from a provider you supply (see
`role_capabilities.guest_auth_adapter` for the guest-auth one).

    require_capability = make_require_capability(
        resolver,
        principal_provider=guest_principal_provider(),
        gate_enabled=lambda: settings.demo_mode,   # off → public tier only
        public_role="beginner",
    )

    @app.get("/golds", dependencies=[Depends(require_capability("golds.view"))])
    def golds(): ...
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from .resolution import RoleResolver


def make_require_capability(
    resolver: RoleResolver,
    *,
    principal_provider: Callable[[], str | None],
    gate_enabled: Callable[[], bool] | None = None,
    public_role: str | None = None,
) -> Callable[[str], Callable[[], None]]:
    """Build a ``require_capability(capability)`` FastAPI dependency factory.

    Args:
        resolver: resolves the current principal's effective role.
        principal_provider: returns the current principal id (or None).
        gate_enabled: whether authorization is active. When it returns False the
            deploy is treated as public — only the public tier is allowed, so a
            gated endpoint fails closed with no identity. Defaults to always on.
        public_role: the role whose bundle defines the public tier; defaults to
            the model's ``default_role``.

    Returns:
        ``require_capability(capability)`` → a FastAPI dependency that returns
        None when allowed and raises ``HTTPException(403)`` otherwise.
    """
    model = resolver.model
    pub_role = public_role if public_role is not None else model.default_role
    gate = gate_enabled or (lambda: True)

    def require_capability(capability: str) -> Callable[[], None]:
        def dependency() -> None:
            if not gate():
                if model.has_capability(pub_role, capability):
                    return
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"'{capability}' requires an authenticated role; "
                        "this deploy is public"
                    ),
                )
            role = resolver.resolve(principal_provider())
            if not model.has_capability(role, capability):
                raise HTTPException(
                    status_code=403,
                    detail=f"requires capability '{capability}'; role '{role}' lacks it",
                )

        return dependency

    return require_capability
