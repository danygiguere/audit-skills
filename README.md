# audit-skills

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version: v0.3.0](https://img.shields.io/badge/version-v0.3.0-blue)](https://github.com/danygiguere/audit-skills/tags)
[![Validate](https://github.com/danygiguere/audit-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/danygiguere/audit-skills/actions/workflows/validate.yml)
![Format: Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-8A2BE2)
![Audits: 34](https://img.shields.io/badge/audits-34-success)
![Works with: Claude Code · Copilot · Cursor · Codex](https://img.shields.io/badge/works%20with-Claude%20Code%20·%20Copilot%20·%20Cursor%20·%20Codex-informational)

Language- and framework-agnostic audit checklists for AI coding agents —
security, correctness, and operability. Works with Claude Code, GitHub
Copilot, Cursor, Codex CLI, OpenCode, and any agent that can read files.
The `audit-*` skills are read-only: they instruct the agent to read code
and report findings; they never run shell commands, or make network calls.

Every checklist is written as **invariants and detection smells**, not
framework APIs, so the same content audits a Rails app, a Spring service,
or an Express API — the agent supplies the framework-specific translation.

> **Works with any language or framework.** Each checklist names eight
> common ecosystems in its concept glossary (Rails, Laravel, Django, Spring,
> Node, Vapor, .NET, Go) — those are recognition shortcuts, **not** a
> support list. The invariants and detection smells are framework-free, so
> the audits apply equally to Phoenix, FastAPI, Ktor, or your in-house
> stack: the agent supplies the translation.

## What's inside

- `AGENTS.md` — a one-page digest of all 34 invariants; copy its content
  into your project's `AGENTS.md` so every agent has it in context.
- `.agents/skills/audit/` — the router skill, with all 34 checklists and
  remediation patterns bundled under `references/` (four categories: access
  & data security, input/API, correctness, operability).
- `.agents/skills/audit-*` — thin per-topic wrapper skills so each checklist
  is individually invocable (`/audit-idor`, `/audit-injection`,
  `/audit-fix-authz`, …). Everything this package installs starts with
  `audit`, so it stays grouped among your other skills.

## The audits

`/audit` runs the full audit — it identifies what the code does and applies
every matching checklist below. Each topic is also individually invocable
(click through to read the checklist itself).

### Access & data security

| Audit                                                                                                 | Checks for                                                                                                                    |
|-------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| [`/audit-authorization`](.agents/skills/audit/references/access-data-security/authorization.md)       | Server-side permission checks at the point of action — privilege escalation, UI-only gating, checks on read but not on mutate |
| [`/audit-authn-session`](.agents/skills/audit/references/access-data-security/authn-session.md)       | Login, logout, and reset flows — session fixation, account enumeration, token expiry and single-use, remember-me storage      |
| [`/audit-idor`](.agents/skills/audit/references/access-data-security/idor.md)                         | Resources fetched or mutated by a request-supplied ID without verifying the requester may touch them                          |
| [`/audit-data-exposure`](.agents/skills/audit/references/access-data-security/data-exposure.md)       | Over-exposed responses, errors, and logs — whole-model serialization, stack traces, PII                                       |
| [`/audit-crypto`](.agents/skills/audit/references/access-data-security/crypto-data-protection.md)     | Password hashing, token randomness, constant-time comparison, homemade crypto, key handling                                   |
| [`/audit-output-encoding`](.agents/skills/audit/references/access-data-security/output-encoding.md)   | XSS — user data rendered into HTML, JS, CSS, URLs, headers, or emails without context-appropriate encoding                    |
| [`/audit-tenant-isolation`](.agents/skills/audit/references/access-data-security/tenant-isolation.md) | Cross-tenant leakage — unscoped queries, tenant-less cache keys, background jobs crossing tenants                             |
| [`/audit-csrf`](.agents/skills/audit/references/access-data-security/csrf.md)                         | State-changing endpoints on cookie/session auth without CSRF token or origin verification                                     |
| [`/audit-mass-assignment`](.agents/skills/audit/references/access-data-security/mass-assignment.md)   | Request payloads bound wholesale onto models — writable role/owner/balance fields, denylists instead of allowlists            |

### Input & API

| Audit                                                                                                      | Checks for                                                                                                                    |
|------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| [`/audit-injection`](.agents/skills/audit/references/input-api-dependency/injection.md)                    | SQL/NoSQL, command, template, and path injection — input concatenated into queries, shells, or templates                      |
| [`/audit-deserialization`](.agents/skills/audit/references/input-api-dependency/deserialization.md)        | Untrusted bytes deserialized into objects — native deserializers, polymorphic JSON/XML typing, unsafe YAML, missing type allowlists, XXE |
| [`/audit-config`](.agents/skills/audit/references/input-api-dependency/config.md)                          | Insecure configuration — debug in production, permissive CORS, missing security headers, cookie flags                         |
| [`/audit-secrets`](.agents/skills/audit/references/input-api-dependency/secrets.md)                        | Hardcoded credentials, secrets in logs or version control, overly broad keys, no rotation path                                |
| [`/audit-api-validation`](.agents/skills/audit/references/input-api-dependency/api-contract-validation.md) | Boundary validation — types, bounds, allowed fields, trusting client-computed values like prices or roles                     |
| [`/audit-file-handling`](.agents/skills/audit/references/input-api-dependency/file-handling.md)            | Path traversal, unvalidated uploads, missing size limits, files served from the web root, zip-slip                            |
| [`/audit-ssrf`](.agents/skills/audit/references/input-api-dependency/ssrf.md)                              | Server-side requests to user-influenced URLs — allowlists, private IP ranges, redirect re-validation; includes open redirects |
| [`/audit-parser-differentials`](.agents/skills/audit/references/input-api-dependency/parser-differentials.md) | Inputs a validator accepts but the consumer reads differently — unanchored regexes, startswith allowlists, two URL parsers, validate-then-reparse |

### Correctness

| Audit                                                                                            | Checks for                                                                                                           |
|--------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| [`/audit-atomicity`](.agents/skills/audit/references/correctness/atomicity.md)                   | Multi-store writes without a transaction — partial state surviving failures                                          |
| [`/audit-idempotency`](.agents/skills/audit/references/correctness/idempotency.md)               | Handlers that misbehave when run twice — webhooks, payments, queue redelivery, double submits                        |
| [`/audit-background-work`](.agents/skills/audit/references/correctness/background-work.md)       | Jobs and consumers — unbounded retries, poison messages, missing timeouts, duplicate or out-of-order delivery        |
| [`/audit-state-management`](.agents/skills/audit/references/correctness/state-management.md)     | Race conditions — check-then-act on shared state without locks, atomic primitives, or constraints                    |
| [`/audit-exception-handling`](.agents/skills/audit/references/correctness/exception-handling.md) | Swallowed errors, blanket catches, lost causes, missing cleanup, and wrong HTTP statuses (404 vs 403, 401, 422, 409) |
| [`/audit-discarded-async`](.agents/skills/audit/references/correctness/discarded-async.md) | Fire-and-forget bugs — promises, futures, or reactive publishers created but never awaited, returned, or composed; bare subscribe; cold writes that silently never run |
| [`/audit-cardinality`](.agents/skills/audit/references/correctness/cardinality.md) | Operations assuming a query matches one row — UPDATE/DELETE on a non-unique column fanning out, findOne/.single() on non-unique fields, columns treated as unique without a DB constraint |
| [`/audit-numeric-precision`](.agents/skills/audit/references/correctness/numeric-precision.md) | Money in float, ad hoc rounding, integer overflow, division remainders that don't sum back, unit/currency mismatches carried only by variable name |
| [`/audit-time-clock`](.agents/skills/audit/references/correctness/time-clock.md) | Naive vs aware datetimes, server-local now(), wall-clock for elapsed time or expiry, DST and calendar math, cross-zone comparisons |

### Operability

| Audit                                                                                          | Checks for                                                                                                |
|------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| [`/audit-nplus1`](.agents/skills/audit/references/operability/nplus1.md)                       | Queries — or HTTP/cache calls — made inside loops over collections                                        |
| [`/audit-observability`](.agents/skills/audit/references/operability/observability.md)         | Silent failures — swallowed errors, logs without identifiers, no metric or alert path                     |
| [`/audit-migration-safety`](.agents/skills/audit/references/operability/migration-safety.md)   | Schema changes that lock tables, destructive changes without expand-contract, unbatched backfills         |
| [`/audit-resource-limits`](.agents/skills/audit/references/operability/resource-limits.md)     | Unbounded work from input — missing pagination, size caps, rate limits, catastrophic regex                |
| [`/audit-blocking-io-async`](.agents/skills/audit/references/operability/blocking-io-async.md) | Blocking calls on event loops or coroutines, CPU work on the scheduler, sync-over-async, missing timeouts |
| [`/audit-schema-design`](.agents/skills/audit/references/operability/schema-design.md) | Missing indexes on FK columns and hot paths, ORM-only relationships without real foreign keys, defaulted ON DELETE, integrity rules only in app code, float money |
| [`/audit-statelessness`](.agents/skills/audit/references/operability/statelessness.md) | State that breaks with a second replica or a deploy — in-memory sessions and counters, static mutable state, local-disk uploads, process-local locks and schedulers |
| [`/audit-caching`](.agents/skills/audit/references/operability/caching.md) | Cache keys missing a user/tenant dimension, stale data after writes, stampede on a hot key, cached errors, per-user responses in a shared or CDN cache |

### Fixes

| Skill                                                                                               | Applies                                                                                                                       |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| [`/audit-fix-authz`](.agents/skills/audit/references/remediation/authz-patterns.md)                 | Remediation patterns for authorization, IDOR, and tenant-isolation findings — scoped queries, policy objects, deny-by-default |
| [`/audit-fix-async`](.agents/skills/audit/references/remediation/async-patterns.md)                 | Remediation patterns for correctness findings — transactions, outbox, idempotency keys, locking, bounded retries              |
| [`/audit-fix-observability`](.agents/skills/audit/references/remediation/observability-patterns.md) | Remediation patterns for observability gaps — structured logging, correlation IDs, RED metrics, symptom-based alerts          |

## Install

Copy the `.agents` folder into your project:

```bash
git clone --depth 1 --branch v0.3.0 \
  https://github.com/danygiguere/audit-skills /tmp/audit-skills \
  && cp -R /tmp/audit-skills/.agents your-project/
```

**Cursor** can also install directly from the repo link, and if you use the
[skills CLI](https://github.com/vercel-labs/skills):
`npx skills add danygiguere/audit-skills --all`.

## Add to your AGENTS.md

This repo's [`AGENTS.md`](AGENTS.md) is the one-page digest of all 34
invariants. Copy its content into your project's `AGENTS.md` (append it if
you already have one — never replace yours): merged there, it gives every
agent ambient awareness of the invariants on every prompt; without it, the
skills only activate when triggered. Its routing table points at the
installed skills folder.

**Claude Code note:** Claude Code does not yet read `.agents/skills/`
([anthropics/claude-code#31005](https://github.com/anthropics/claude-code/issues/31005)).
Bridge it with:

```bash
mkdir -p .claude && ln -s ../.agents/skills .claude/skills
echo '@AGENTS.md' > CLAUDE.md          # if you don't already have a CLAUDE.md
```

## Use

- **Automatic** — ask your agent to "review this endpoint" / "audit this
  diff"; the skills trigger on their descriptions.
- **By command** — `/audit` for a full audit, or per topic:
  `/audit-idor`, `/audit-injection`, `/audit-atomicity`, … All of them
  audit your current diff by default; name a file, folder, or branch to
  audit something else.
- **By name** — "run the idempotency checklist on this webhook handler".
- **Fixes** — after findings are confirmed: `/audit-fix-authz`,
  `/audit-fix-async`, `/audit-fix-observability` (see "How fixes work").

## How fixes work

Audits and fixes are deliberately separate steps. `/audit` and the
`audit-*` checklists only **find and report** — they never change code.
Fixing happens when you ask for it: say "fix those" after a report, or run
an `audit-fix-*` command.

Every finding has a fix available; what differs is where it lives:

**Most topics — the fix is in the checklist itself.** Each checklist's
`Example` section shows the vulnerable shape next to the fixed shape. For
topics like injection, secrets, output encoding, or N+1 queries, the fix is
mechanical and has one right answer (parameterize the query, move the secret
to the environment, bulk-load before the loop). When you say "fix it", the
agent applies that fixed shape — no extra command needed.

**Eight topics — the fix is an architectural choice.** Some findings have
several valid fixes with real trade-offs (an idempotency bug: dedupe table,
idempotency key, UPSERT, or an absolute-state write?). Those topics point to
a remediation playbook that walks the agent through choosing:

| Findings from                                             | Playbook                                | Command                    |
|-----------------------------------------------------------|-----------------------------------------|----------------------------|
| authorization, IDOR, tenant isolation                     | `remediation/authz-patterns.md`         | `/audit-fix-authz`         |
| atomicity, idempotency, background work, state management | `remediation/async-patterns.md`         | `/audit-fix-async`         |
| observability                                             | `remediation/observability-patterns.md` | `/audit-fix-observability` |

Either way, the flow is the same: **audit → confirmed findings → ask for the
fix.** Fixes follow the same rules everywhere: the smallest change that
restores the invariant, matching the surrounding code style, with a test
demonstrating the fix — and never mixed with unrelated refactoring.

## Versioning

The canonical version lives in [`VERSION`](VERSION). It is stamped into the
two artifacts that travel into your project: the `audit` skill (a `version:`
field in its frontmatter plus a source footer) and the `AGENTS.md` digest
(footer). Installed copies therefore always say what version they are and
where they come from — compare your stamp against this repo's `VERSION` to
know whether you're outdated. (No need to copy `VERSION` into your
project — the stamps travel with the artifacts.) Your agent can do it for you: "check whether
my audit-skills are up to date" gives it everything it needs.

## License

[MIT](LICENSE)
