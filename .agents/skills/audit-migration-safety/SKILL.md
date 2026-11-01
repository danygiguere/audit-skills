---
name: audit-migration-safety
description: Zero-downtime migration checklist. Use when reviewing database migrations or schema changes — locks, backfills, destructive changes, rollback plans.
---

Read `../audit/references/operability/migration-safety.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
