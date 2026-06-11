# audit-knowledge

Language- and framework-agnostic audit checklists for AI coding agents —
security, correctness, and operability. Works with Claude Code, GitHub
Copilot, Cursor, Codex CLI, OpenCode, and any agent that can read files.

Every checklist is written as **invariants and detection smells**, not
framework APIs, so the same content audits a Rails app, a Spring service,
or an Express API — the agent supplies the framework-specific translation.

## What's inside

- `AGENTS.md` — a one-page digest of all 22 invariants, always in context.
- `.agents/skills/audit/` — the router skill, with all 22 checklists and
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
cp AGENTS.md <your-project>/           # or merge into your existing AGENTS.md
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
  `/audit-fix-async`, `/audit-fix-observability`.
