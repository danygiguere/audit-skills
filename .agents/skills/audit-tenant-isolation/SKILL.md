---
name: audit-tenant-isolation
description: Multi-tenant isolation checklist. Use when reviewing queries, caches, or background jobs in a multi-tenant app for cross-tenant data leakage — tenant scoping, shared cache keys.
---

Read `../audit/references/access-data-security/tenant-isolation.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
