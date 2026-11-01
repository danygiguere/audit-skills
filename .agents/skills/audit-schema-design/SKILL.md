---
name: audit-schema-design
description: Database schema design checklist (indexes, foreign keys, constraints). Use when reviewing migrations, new tables or columns, slow queries, missing indexes, foreign-key and ON DELETE behavior, or integrity rules enforced only in app code.
---

Read `../audit/references/operability/schema-design.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
