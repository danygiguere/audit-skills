---
name: audit-idor
description: Insecure direct object reference checklist. Use when code fetches or mutates a resource using an ID, slug, UUID, or filename taken from the request.
---

Read `../audit/references/access-data-security/idor.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
