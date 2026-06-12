---
name: audit
description: Full security, correctness, and operability audit of code. Use when reviewing a diff, endpoint, or feature for vulnerabilities or bugs without a specific topic in mind — security review, audit, code review for safety, "check this for issues".
---

# Audit procedure

1. **Identify** what the code under audit does. Trace the data flow: what
   inputs arrive, what is looked up, what is written, what is rendered or
   returned, what runs async.
2. **Load** only the checklist files matching that behavior, from the map
   below.
3. **Check** each invariant in the loaded files against the code.
4. **Verify before reporting**: load `references/methodology/verify.md`
   and run every candidate through it — name the attacker and the victim,
   hunt for existing mitigations in the surrounding code (middleware, base
   classes, decorators, callers), and when auditing a diff, anchor each
   finding to the lines that introduce or enable it. A candidate survives
   only if you cannot refute it with cited evidence.
5. **Report** each finding with: severity, `file:line`, the violated
   invariant, and a one-line fix direction. Say explicitly which checklists
   were applied and came back clean.
6. **Fix only on request**: when the user asks for remediation, load the
   matching `references/remediation/` file and apply its patterns.

Do not manufacture findings for topics that don't apply (e.g., CSRF on a
token-authenticated API, tenant isolation in a single-tenant app).

# What to load

Paths relative to this skill's directory. Load every row that matches; skip
the rest.

| The code…                                            | Read                                                                                                                                       |
|------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| Gates actions by role, permission, or ownership      | `references/access-data-security/authorization.md`                                                                                         |
| Handles login, logout, reset, tokens, sessions       | `references/access-data-security/authn-session.md`                                                                                         |
| Fetches/mutates a resource by an ID from the request | `references/access-data-security/idor.md` + `references/access-data-security/authorization.md`                                             |
| Serializes models, formats errors, writes logs       | `references/access-data-security/data-exposure.md`                                                                                         |
| Hashes, encrypts, generates or compares secrets      | `references/access-data-security/crypto-data-protection.md`                                                                                |
| Renders user data into HTML/JS/URLs/headers/emails   | `references/access-data-security/output-encoding.md`                                                                                       |
| Touches data or caches in a multi-tenant app         | `references/access-data-security/tenant-isolation.md`                                                                                      |
| Changes state with cookie/session-based auth         | `references/access-data-security/csrf.md`                                                                                                  |
| Binds request payloads onto models/entities          | `references/access-data-security/mass-assignment.md`                                                                                       |
| Builds queries/commands/templates/paths from input   | `references/input-api-dependency/injection.md`                                                                                             |
| Configures CORS, headers, cookies, debug, env        | `references/input-api-dependency/config.md`                                                                                                |
| Touches API keys, credentials, tokens                | `references/input-api-dependency/secrets.md`                                                                                               |
| Validates (or should validate) request input         | `references/input-api-dependency/api-contract-validation.md`                                                                               |
| Accepts, stores, processes, or serves files          | `references/input-api-dependency/file-handling.md`                                                                                         |
| Makes network requests to user-influenced URLs       | `references/input-api-dependency/ssrf.md`                                                                                                  |
| Adds validators, regexes, allowlists, or parsing | `references/input-api-dependency/parser-differentials.md` |
| Writes to multiple tables/stores/systems at once     | `references/correctness/atomicity.md`                                                                                                      |
| Handles payments, webhooks, retries, emails          | `references/correctness/idempotency.md`                                                                                                    |
| Runs jobs, scheduled tasks, or queue consumers       | `references/correctness/background-work.md`                                                                                                |
| Shares mutable state, caches, counters               | `references/correctness/state-management.md`                                                                                               |
| Catches/throws errors, maps errors to HTTP statuses  | `references/correctness/exception-handling.md`                                                                                             |
| Creates promises, futures, tasks, or publishers | `references/correctness/discarded-async.md` |
| Loads related data inside a loop over a collection   | `references/operability/nplus1.md`                                                                                                         |
| Adds endpoints/jobs, handles errors                  | `references/operability/observability.md`                                                                                                  |
| Changes database schema                              | `references/operability/migration-safety.md` + `references/operability/schema-design.md`                                                                                               |
| Does work proportional to input size                 | `references/operability/resource-limits.md`                                                                                                |
| Runs async/await, event-loop, or coroutine code      | `references/operability/blocking-io-async.md`                                                                                              |
| Is meant to scale out / run as multiple replicas | `references/operability/statelessness.md` |
| — Verifying candidate findings (step 4, always) | `references/methodology/verify.md` |
| — Fixing confirmed findings                          | `references/remediation/authz-patterns.md`, `references/remediation/async-patterns.md`, `references/remediation/observability-patterns.md` |
