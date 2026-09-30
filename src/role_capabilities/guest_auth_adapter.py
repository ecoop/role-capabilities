# Copyright (c) 2026 Eric Cooper.
"""guest-auth adapter — turn the current guest identity into a principal id.

Optional: importing this module needs the ``guest-auth`` extra
(``role-capabilities[guest-auth]``). It is the default way to feed
`role_capabilities.fastapi_dep.make_require_capability` a current principal, but
nothing in the core depends on guest-auth — an app on a different identity system
supplies its own provider callable instead.

The principal key is yours to choose (brief requirement #2): key by the token
(the default), or by a stable id like a profile/recipient so rotating a token
never drops a role.
"""

from __future__ import annotations

from collections.abc import Callable

from guest_auth import GuestIdentity, get_current_guest


def guest_principal_provider(
    principal_key: Callable[[GuestIdentity], str] | None = None,
) -> Callable[[], str | None]:
    """A provider that maps the current guest to its principal id, or None.

    Args:
        principal_key: how to derive the principal from a `GuestIdentity`.
            Defaults to the guest's token; pass e.g. ``lambda g: g.recipient`` to
            key by a stable id instead.

    Returns:
        A zero-arg callable returning the current principal id, or None when there
        is no authenticated guest.
    """
    key = principal_key or (lambda g: g.token)

    def provider() -> str | None:
        guest = get_current_guest()
        return key(guest) if guest is not None else None

    return provider
