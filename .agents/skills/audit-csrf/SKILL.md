---
name: audit-csrf
description: Cross-site request forgery checklist. Use when reviewing state-changing endpoints in apps with cookie or session-based authentication — CSRF tokens, SameSite, origin checks. Does not apply to pure token-based APIs.
---

Read `../audit/references/access-data-security/csrf.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
