# Phase 10: Support ${env:KEY} config placeholder - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the placeholder resolution system in `value_resolver.py` with an `${env:KEY}` namespace. When a workflow JSON `value` field contains `${env:KEY}`, the framework resolves it against the active env YAML config file at action-dispatch time. Allows account numbers, credentials, and environment-specific IDs to live in `configs/env.{env}.yaml` rather than being hardcoded in workflow JSON.

Pure extension of the existing Phase 4 placeholder infrastructure — no schema changes, no new element types.

</domain>

<decisions>
## Implementation Decisions

### D-01: Key scope — any YAML key
`${env:KEY}` resolves against **any key** present in the active `env.{env}.yaml` file. No dedicated section needed. Users simply add custom keys (e.g. `account_number`, `login_password`) alongside existing infra keys (`base_url`, `browser`, etc.). No YAML restructuring required.

### D-02: Missing key — raise ValueError
When `${env:KEY}` is used and KEY is not found in the loaded YAML data, raise `ValueError` with a clear message (e.g. `"Unknown env config key 'MISSING_KEY'. Available keys: [...]"`). Consistent with the existing behavior for unregistered `${placeholder}` tokens (Phase 4 pattern). Fails loudly at resolve time so the missing key is surfaced immediately.

No fallback syntax (`${env:KEY:default}`) — this is deferred scope.

### D-03: Resolution priority — YAML only
`${env:KEY}` reads **only** from the env YAML dict. Shell env vars and `.env` overrides do **not** apply to `${env:KEY}` lookups. This intentionally differs from `AppConfig._resolve()` (which has env-var-wins priority) — `${env:KEY}` resolves exactly what is in the YAML file, nothing more. Simpler reasoning, simpler tests.

### D-04: Config injection — module-level singleton
A `configure_env_resolver(data: dict)` function in `value_resolver.py` stores the YAML dict in a module-level variable (e.g. `_ENV_CONFIG: dict = {}`). This function is called once at `AppConfig.__init__` after the YAML is loaded. No constructor changes to `ValueResolver`. No file I/O at resolve time. Follows the same module-level state pattern as `_sin_state` (existing precedent).

`resolve_dynamic_value()` handles the `env:KEY` prefix: when the captured group starts with `env:`, it looks up the suffix in `_ENV_CONFIG` rather than `PLACEHOLDER_REGISTRY`.

### Claude's Discretion
- Exact error message wording and format
- Naming of the module-level variable (`_ENV_CONFIG` or similar)
- Where in `AppConfig.__init__` the `configure_env_resolver()` call is placed
- Test design (mock dict vs real YAML fixture)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing placeholder infrastructure
- `src/actions/value_resolver.py` — `_PLACEHOLDER_PATTERN`, `PLACEHOLDER_REGISTRY`, `resolve_dynamic_value()`, `ValueResolver` — all code that Phase 10 extends
- `src/core/config.py` — `AppConfig.__init__` and `_load_yaml()` — where `configure_env_resolver()` must be called

### Env config files
- `configs/env.dev.yaml` — representative YAML structure (flat key/value); keys added here are what `${env:KEY}` resolves
- `configs/env.qa.yaml` — same structure for QA
- `configs/env.prod.yaml` — same structure for prod

### Tests reference
- `tests/unit/test_value_resolver.py` — existing test class structure; new `TestEnvPlaceholder` class appends here (TDD pattern from Phase 4 and 9)

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_PLACEHOLDER_PATTERN` in `value_resolver.py`: already captures `env:KEY` as the full match group — no regex change needed
- `PLACEHOLDER_REGISTRY` dispatch in `resolve_dynamic_value()`: a single `if key.startswith("env:")` branch before the registry lookup handles the namespace
- `_sin_state` module-level dict: precedent for module-level mutable state in `value_resolver.py`

### Established Patterns
- TDD RED→GREEN: write failing import/test first (Phase 4 and 9 both followed this)
- Module-level state: `_sin_state` shows the pattern for a module-level variable set externally
- `ValueError` on unknown token: Phase 4 established this — Phase 10 extends it to missing env keys

### Integration Points
- `AppConfig.__init__` in `src/core/config.py` — must call `configure_env_resolver(self._data)` after `self._data` is set
- `resolve_dynamic_value()` in `value_resolver.py` — add `env:` prefix check before the `PLACEHOLDER_REGISTRY` lookup
- `tests/unit/test_value_resolver.py` — append `TestEnvPlaceholder` class

</code_context>

<specifics>
## Specific Ideas

- Users write `${env:account_number}` or `${env:login_password}` in workflow JSON `value` fields
- The same `ValueResolver._resolve_string` → `resolve_dynamic_value` path is used; no action dispatch changes needed
- `configure_env_resolver({})` (empty dict) as the default means the module works even before `AppConfig` is instantiated (raises `ValueError` on any `${env:*}` access until configured, which is correct)

</specifics>

<deferred>
## Deferred Ideas

- **Fallback syntax** `${env:KEY:default}` — explicitly out of scope for this phase; can be a follow-on phase
- **Env var override support** for `${env:KEY}` — user chose YAML-only; revisit if CI override use case arises
- **Nested YAML keys** (e.g. `${env:credentials.username}`) — deferred; flat keys only for now

None of the above block Phase 10 delivery.

</deferred>

---

*Phase: 10-support-env-placeholder*
*Context gathered: 2026-05-29*
