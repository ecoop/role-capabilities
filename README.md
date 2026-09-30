# role-capabilities

App-agnostic, capability-based roles for Python apps. Declare your own closed
set of capabilities and your own role → capability bundles; resolve a
principal's effective role from a seed plus append-only overrides; and check
`has_capability(actor, capability)` anywhere — inside a web request or a plain
CLI command.

Extracted from [Rulebook](https://github.com/ecoop/rulebook)'s RBAC (design and
scope: [ecoop/rulebook#220](https://github.com/ecoop/rulebook/issues/220)).
Rulebook is the first consumer. The core depends on no identity library —
[guest-auth](https://pypi.org/project/guest-auth/) integrates as an optional
adapter, so an app can key roles by whatever stable principal it already has.

**Status: 0.1.0.** The engine is all here — capabilities, role ordering,
resolution over a pluggable `RoleStore` (in-memory + GCS), the role-admin
read/write surface, and the optional FastAPI + guest-auth adapters. In use by
[Rulebook](https://github.com/ecoop/rulebook), its first consumer. The API may
still shift until `1.0` (see [CHANGELOG](CHANGELOG.md)).

## Usage — the capability engine

```python
from role_capabilities import CapabilityModel

MODEL = CapabilityModel(
    capabilities={"read", "write", "admin"},
    roles={
        "guest":  frozenset(),
        "member": {"read", "write"},
        "owner":  {"read", "write", "admin"},
    },
    default_role="member",
    aliases={"legacy_admin": "owner"},  # old ids keep resolving after a rename
)

MODEL.has_capability("member", "write")   # True
MODEL.has_capability("member", "admin")   # False
MODEL.capabilities_for("wizard")          # frozenset()  — unknown role fails closed
MODEL.canonical_role("legacy_admin")      # "owner"

MODEL.ordered_roles()                     # ("guest", "member", "owner")  — low → high
MODEL.role_order("owner")                 # 2   (-1 for an unranked role)
```

Roles order as declared, low → high; pass `order=[...]` to set the ladder
explicitly if your `roles` dict isn't already in ladder order. Ordering is a
presentational/sort axis only — no authorization check reads it — and names,
colors, and descriptions stay in the app.

## Usage — resolving a principal's role

```python
from role_capabilities import RoleResolver, MemoryRoleStore, GcsRoleStore

resolver = RoleResolver(
    model=MODEL,
    store=MemoryRoleStore(),                    # or GcsRoleStore("bucket", "roles.jsonl")
    seed={"alice": "owner"},                    # static baseline, keyed by principal
)
resolver.assert_seeded("owner")                 # bootstrap guard — fail closed at startup

resolver.resolve("alice")                       # "owner"  (seed)
resolver.resolve("bob")                         # "member" (default)
resolver.has_capability("bob", "admin")         # False

resolver.set_role("bob", "owner", actor="alice")  # audited override; visible at once
resolver.resolve("bob")                         # "owner"
resolver.reset_role("bob", actor="alice")       # back to seed/default

resolver.assignments()                          # {principal: role} for everyone with an assignment
resolver.roster(["alice", "bob", "carol"])      # resolve each, defaults included — for an admin table
```

Role administration lives here — change/reset, and the `assignments` / `roster`
read helpers. **Identity** lifecycle (adding, removing, or renaming a user) is
your identity layer's job, not this library's; supply your user list to `roster`
to show everyone.

## Usage — FastAPI + guest-auth (optional adapters)

The core is framework-free. Two optional adapters (their own modules, so the core
imports need no extra dependency) wire it into a FastAPI app authenticated by
guest-auth:

```python
from fastapi import Depends
from role_capabilities.fastapi_dep import make_require_capability
from role_capabilities.guest_auth_adapter import guest_principal_provider

require_capability = make_require_capability(
    resolver,
    principal_provider=guest_principal_provider(),   # or lambda: g.recipient to key by a stable id
    gate_enabled=lambda: settings.demo_mode,         # off → public tier only (fails closed)
    public_role="beginner",
)

@app.get("/golds", dependencies=[Depends(require_capability("golds.view"))])
def golds(): ...
```

`make_require_capability` needs the `[fastapi]` extra; `guest_principal_provider`
needs `[guest-auth]`. On a different stack, supply your own `principal_provider`
callable and skip both.

Resolution is **override ▸ seed ▸ default**. Overrides are an append-only log
(latest row wins, `reset` clears), read through a `RoleStore` and TTL-cached; a
backend read failure reuses the last good snapshot rather than failing the check.
Everything is keyed by an app-supplied **principal id** and the checks take it
explicitly, so the resolver works in a web request or a plain CLI / batch job.

Construction validates the declaration (every bundle stays within the closed set;
`default_role` and alias targets must be real roles) and raises `ValueError` on a
malformed one; queries fail closed.

## Install

```
pip install role-capabilities                 # core (pure stdlib)
pip install "role-capabilities[guest-auth]"   # + guest-auth current-actor adapter
pip install "role-capabilities[gcs]"          # + GCS RoleStore backend
pip install "role-capabilities[fastapi]"      # + require_capability dependency
```

## Design

- **App-defined vocabulary** — no built-in capability names; you declare the
  closed set and the role → capability bundles.
- **Keyed by a stable principal**, not a token — rotating a token never drops a
  role.
- **Pluggable persistence** — a small `RoleStore` (read all rows / append a row)
  with GCS and SQL backends; seed + append-only overrides, latest row wins, a
  `reset` row falls back to the seed, TTL-cached reads.
- **Works with no web request** — the core check takes the actor explicitly, so
  it runs in a CLI or a Cloud Run job; a thin FastAPI `require_capability` sits
  on top.
- **Fail-closed** — unknown principal → the default role; unresolvable → the
  public tier; refuses to start with no superuser seeded.

See [ecoop/rulebook#220](https://github.com/ecoop/rulebook/issues/220) for the
full extraction plan.

_Last updated: 2026-09-30_

