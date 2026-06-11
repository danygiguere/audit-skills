# audit-skills

Language- and framework-agnostic audit checklists for AI coding agents —
security, correctness, and operability. Works with Claude Code, GitHub
Copilot, Cursor, Codex CLI, OpenCode, and any agent that can read files.

Every checklist is written as **invariants and detection smells**, not
framework APIs, so the same content audits a Rails app, a Spring service,
or an Express API — the agent supplies the framework-specific translation.

## What's inside

- `.agents/skills/audit/DIGEST.md` — a one-page digest of all 23 invariants,
  designed to be merged into (or referenced from) your project's `AGENTS.md`.
- `.agents/skills/audit/` — the router skill, with all 23 checklists and
  remediation patterns bundled under `references/` (four categories: access
  & data security, input/API, correctness, operability).
- `.agents/skills/audit-*` — thin per-topic wrapper skills so each checklist
  is individually invocable (`/audit-idor`, `/audit-injection`,
  `/audit-fix-authz`, …). Everything this package installs starts with
  `audit`, so it stays grouped among your other skills.

## Install

**Option 1 — add-skill CLI (any Agent Skills tool):**

```bash
npx add-skill <this-repo-url>
```

**Option 2 — Cursor:** install directly from the repo link
(Cursor reads `.agents/skills/` natively).

**Option 3 — manual copy:**

```bash
cp -R .agents <your-project>/
```

## Add to your AGENTS.md

The digest gives every agent ambient awareness of the invariants on every
prompt — without it, the skills only activate when triggered. Two levels:

**Strongest — paste it in:** copy the contents of
`.agents/skills/audit/DIGEST.md` into your project's `AGENTS.md`. The
invariants are then literally in context on every prompt.

**Leaner — point at it:** add one line to your `AGENTS.md`:

```markdown
Before reviewing, auditing, or writing code, apply the invariants in `.agents/skills/audit/DIGEST.md`.
```

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
  `/audit-idor`, `/audit-injection`, `/audit-atomicity`, …
- **By name** — "run the idempotency checklist on this webhook handler".
- **By path** — works in any tool: "review this against
  `.agents/skills/audit/references/correctness/atomicity.md`".
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
