# Engineering audit digest

Apply the invariants below to all code you review, audit, or generate.
Detailed per-topic checklists live in the installed `audit` skill under
`references/` — by default `.agents/skills/audit/references/`. Read the
matching file (map at the bottom) before doing an in-depth audit.

## Invariants (always apply)

### Access & data security

- **Authorization** — every state-changing or sensitive action is permission-checked server-side at the point of action,
  not only in the UI or routing layer.
- **Authentication & sessions** — sessions are regenerated on login and invalidated on logout; credential and reset
  flows do not reveal whether an account exists.
- **IDOR** — any resource looked up by an identifier from the request is verified as owned by or visible to the current
  principal; a valid ID is not authorization.
- **Data exposure** — responses, errors, and logs contain only fields explicitly intended for the consumer; never whole
  models, stack traces, or PII by default.
- **Crypto & data protection** — passwords use adaptive hashing; tokens come from a CSPRNG; secret comparisons are
  constant-time; no homemade crypto.
- **Output encoding** — every user-controlled value rendered into HTML, JS, CSS, URLs, headers, or emails is encoded for
  that exact context.
- **Tenant isolation** — in multi-tenant code, every query, cache key, and background job is scoped by tenant; no
  implicit global reads.
- **CSRF** — state-changing endpoints authenticated by cookies verify a CSRF token or origin (not applicable to pure
  token-based APIs).
- **Mass assignment** — request data is never bound wholesale onto models; every binding site has an explicit,
  per-context allowlist of writable fields (allowlists, never denylists).

### Input, API & dependencies

- **Injection** — queries, shell commands, templates, and paths are built with parameterization or escaping APIs, never
  by concatenating input.
- **Configuration** — production config denies by default: debug off, CORS explicit, security headers present, cookies
  Secure/HttpOnly.
- **Secrets** — credentials live in env vars or secret managers; never hardcoded, logged, or committed; rotation is
  possible.
- **API contract & validation** — every input is validated at the boundary for type, bounds, and allowed fields; unknown
  fields are rejected or ignored explicitly.
- **File handling** — file paths are never derived from raw input; uploads are constrained by type, size, and storage
  location; served files cannot escape their root.
- **SSRF** — server-side requests to user-influenced URLs validate the destination against an allowlist; redirect
  targets count as destinations.
- **Parser differentials** — a gate must interpret input exactly as its consumer does: anchored matches, exact-host
  allowlists, validate the parsed object and pass that object on — never validate raw input and re-parse it.

### Correctness

- **Atomicity** — writes that must succeed together run in one transaction or have explicit compensation; partial state
  never survives a failure.
- **Idempotency** — any handler that can run twice (retries, webhooks, double submits) produces the same outcome as
  running once.
- **Background work** — jobs have bounded retries, dead-letter handling, and timeouts, and tolerate duplicate or
  out-of-order delivery.
- **State management** — no check-then-act on shared state without a lock, atomic primitive, or database constraint
  backing it.
- **Exception handling** — errors are handled or propagated, never swallowed; catches are narrow, causes preserved,
  resources released; HTTP boundaries return the status the condition means (404/401/403/422/409, never 200-with-error).
- **Discarded async work** — every promise, future, task, or publisher is awaited, returned, composed, or
  deliberately detached with error handling; a cold producer that is never subscribed silently never runs.

### Operability

- **N+1 queries** — never query inside a loop over a collection; load related data in bulk.
- **Observability** — every failure path logs with context; new endpoints and jobs emit enough signal for their failures
  to be visible in production.
- **Migration safety** — schema changes deploy without downtime: no long locks, destructive changes split across
  releases, rollback considered.
- **Resource limits** — all work driven by input size is bounded: pagination, body and upload caps, rate limits, no
  catastrophic regex.
- **Blocking I/O in async code** — code on a cooperative scheduler (event loop, coroutines, reactor) never blocks: no
  sync I/O, sleeps, or CPU-heavy work on the loop; blocking work is offloaded and outbound calls have timeouts.
- **Schema design** — relationships enforced by real foreign keys with deliberate ON DELETE; hot query paths backed
  by indexes; integrity rules (NOT NULL, unique, checks) live in the schema, not only in app validation.
- **Statelessness** — in replicated apps, state lives in process memory or local disk only if losing it is harmless
  and no peer replica needs it; sessions, counters, locks, uploads, and schedules live in shared stores.

## Deep checklists — what to read when

Read only the files matching what the code under audit does. Paths are
relative to the `audit` skill's `references/` directory (by default
`.agents/skills/audit/references/`); if a path does not resolve, locate the
`audit` skill folder in your skills directory and resolve from there:

| The code…                                            | Read                                                                                                      |
|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Gates actions by role, permission, or ownership      | `access-data-security/authorization.md`                                                                   |
| Handles login, logout, reset, tokens, sessions       | `access-data-security/authn-session.md`                                                                   |
| Fetches/mutates a resource by an ID from the request | `access-data-security/idor.md` + `access-data-security/authorization.md`                                  |
| Serializes models, formats errors, writes logs       | `access-data-security/data-exposure.md`                                                                   |
| Hashes, encrypts, generates or compares secrets      | `access-data-security/crypto-data-protection.md`                                                          |
| Renders user data into HTML/JS/URLs/headers/emails   | `access-data-security/output-encoding.md`                                                                 |
| Touches data or caches in a multi-tenant app         | `access-data-security/tenant-isolation.md`                                                                |
| Changes state with cookie/session-based auth         | `access-data-security/csrf.md`                                                                            |
| Binds request payloads onto models/entities          | `access-data-security/mass-assignment.md`                                                                 |
| Builds queries/commands/templates/paths from input   | `input-api-dependency/injection.md`                                                                       |
| Configures CORS, headers, cookies, debug, env        | `input-api-dependency/config.md`                                                                          |
| Touches API keys, credentials, tokens                | `input-api-dependency/secrets.md`                                                                         |
| Validates (or should validate) request input         | `input-api-dependency/api-contract-validation.md`                                                         |
| Accepts, stores, processes, or serves files          | `input-api-dependency/file-handling.md`                                                                   |
| Makes network requests to user-influenced URLs       | `input-api-dependency/ssrf.md`                                                                            |
| Adds validators, regexes, allowlists, or parsing    | `input-api-dependency/parser-differentials.md`                                                            |
| Writes to multiple tables/stores/systems at once     | `correctness/atomicity.md`                                                                                |
| Handles payments, webhooks, retries, emails          | `correctness/idempotency.md`                                                                              |
| Runs jobs, scheduled tasks, or queue consumers       | `correctness/background-work.md`                                                                          |
| Shares mutable state, caches, counters               | `correctness/state-management.md`                                                                         |
| Catches/throws errors, maps errors to HTTP statuses  | `correctness/exception-handling.md`                                                                       |
| Creates promises, futures, tasks, or publishers     | `correctness/discarded-async.md`                                                                          |
| Loads related data inside a loop over a collection   | `operability/nplus1.md`                                                                                   |
| Adds endpoints/jobs, handles errors                  | `operability/observability.md`                                                                            |
| Changes database schema                              | `operability/migration-safety.md` + `operability/schema-design.md`                                        |
| Does work proportional to input size                 | `operability/resource-limits.md`                                                                          |
| Runs async/await, event-loop, or coroutine code      | `operability/blocking-io-async.md`                                                                        |
| Is meant to scale out / run as multiple replicas    | `operability/statelessness.md`                                                                            |
| — Verifying candidate findings before reporting     | `methodology/verify.md`                                                                                   |
| — Fixing confirmed findings                          | `remediation/authz-patterns.md`, `remediation/async-patterns.md`, `remediation/observability-patterns.md` |

Do not manufacture findings for topics that do not apply (e.g., CSRF on a
token-authenticated API). Verify every finding against surrounding code
(middleware, base classes, callers) before reporting it.

---

*From [audit-skills](https://github.com/danygiguere/audit-skills) v0.1.0 —
the digest and the audit skills are maintained there; compare with the
repo's `VERSION` file to check whether your copy is outdated.*
