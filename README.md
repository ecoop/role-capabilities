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

**Status: scaffold.** The API sketched below is the target shape; the extraction
lands incrementally per the design issue. Not yet published to PyPI.

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
