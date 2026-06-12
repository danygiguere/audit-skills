---
name: audit-atomicity
description: Transactional-integrity checklist. Use when one operation writes to multiple tables, stores, or external systems and partial failure would corrupt state.
---

Read `../audit/references/correctness/atomicity.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
