---
name: audit-cardinality
description: Query cardinality checklist. Use when an UPDATE or DELETE keys on a non-unique column (e.g. WHERE name = ?) and may hit the wrong rows, when findOne/.single()/.first() runs on a non-unique field, or when a column is treated as unique in app code without a database UNIQUE constraint.
---

Read `../audit/references/correctness/cardinality.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
