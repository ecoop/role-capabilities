# Changelog

All notable changes to `role-capabilities` are documented here. This project
follows [Semantic Versioning](https://semver.org/); the API may still change
between `0.x` releases.

## 0.1.0 — 2026-09-30

First release. The capability-based RBAC engine extracted from
[Rulebook](https://github.com/ecoop/rulebook) (design: ecoop/rulebook#220), now
its first consumer.

### Added

- **`CapabilityModel`** — an app-injected closed capability set plus role →
  capability bundles. Alias-aware queries (`has_capability`, `capabilities_for`,
  `is_valid_role`, `canonical_role`), fingerprints (`capability_fingerprint`,
  `role_fingerprint`), and the presentational role ladder (`order`,
  `ordered_roles`, `role_order`). Construction validates the declaration and
  fails loud; queries fail closed.
- **`RoleStore`** protocol with `MemoryRoleStore` and `GcsRoleStore` backends,
  and **`replay_overrides`** — append-only override replay (latest row wins,
  `reset` clears, keyed by an app-supplied principal).
- **`RoleResolver`** — resolve a principal's effective role (override ▸ seed ▸
  default), TTL-cached with last-good fallback, audited `set_role` / `reset_role`,
  `assert_seeded` bootstrap guard, and the `assignments` / `roster` read helpers.
- **Optional adapters** (own modules; the core imports need no extra dependency):
  `role_capabilities.fastapi_dep.make_require_capability` (`[fastapi]` extra) and
  `role_capabilities.guest_auth_adapter.guest_principal_provider`
  (`[guest-auth]` extra).

### Notes

- Python `>=3.11`. Core has no runtime dependencies; `guest-auth`, GCS, and
  FastAPI are optional extras.
- Identity lifecycle (adding, removing, or renaming a user) is intentionally out
  of scope — it belongs to the app's identity layer.
