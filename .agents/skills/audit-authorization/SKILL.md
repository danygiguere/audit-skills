---
name: audit-authorization
description: Access-control audit checklist. Use when reviewing endpoints or handlers that gate actions by role, permission, or ownership, or when checking for privilege escalation.
---

Read `../audit/references/access-data-security/authorization.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
