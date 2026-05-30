# Phase 10: Support ${env:KEY} config placeholder - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 10-support-env-placeholder
**Areas discussed:** Key scope, Missing key, Resolution priority, Config injection

---

## Key scope in YAML

| Option | Description | Selected |
|--------|-------------|----------|
| Any YAML key | ${env:KEY} accesses any key in env.{env}.yaml; no restructuring needed | ✓ |
| workflow_vars: section only | Dedicated section in YAML keeps infra keys separate | |
| Separate workflow-vars YAML file | A separate file for test values, infra YAML untouched | |

**User's choice:** Any YAML key
**Notes:** Users add custom keys alongside existing ones (`base_url`, etc.) — simplest approach, no migration needed.

---

## Error on missing key

| Option | Description | Selected |
|--------|-------------|----------|
| Raise ValueError | Consistent with unknown placeholder behavior today | ✓ |
| Fallback syntax ${env:KEY:default} | Extended syntax; more flexible but adds parsing complexity | |
| Return empty string silently | Never fails — silent failures are hard to debug | |

**User's choice:** Raise ValueError
**Notes:** Consistent with Phase 4 pattern. Fails loudly so missing keys are surfaced immediately at resolve time.

---

## Resolution priority

| Option | Description | Selected |
|--------|-------------|----------|
| Env vars win, then YAML | Mirrors AppConfig priority; CI can override without touching YAML | |
| YAML only | Reads only env.{env}.yaml; simpler to reason about and test | ✓ |

**User's choice:** YAML only — ignore env vars
**Notes:** Intentional departure from AppConfig._resolve() priority. ${env:KEY} resolves exactly what is in the YAML file.

---

## Config injection into ValueResolver

| Option | Description | Selected |
|--------|-------------|----------|
| Module-level singleton set at startup | configure_env_resolver(data) called from AppConfig.__init__ | ✓ |
| Injected into ValueResolver constructor | ValueResolver(config=AppConfig()); most testable but requires updating all instantiation sites | |
| ValueResolver re-reads YAML itself | File I/O at each resolve call; no injection needed | |

**User's choice:** Module-level singleton (configure_env_resolver pattern)
**Notes:** Follows existing _sin_state precedent in value_resolver.py. No constructor changes to ValueResolver.

---

## Claude's Discretion

- Exact error message wording and format
- Naming of the module-level config variable
- Where in AppConfig.__init__ the configure_env_resolver() call is placed
- Test design details

## Deferred Ideas

- Fallback syntax `${env:KEY:default}` — out of scope for this phase
- Env var override support for ${env:KEY} — user chose YAML-only
- Nested YAML keys (dot notation) — flat keys only for now
