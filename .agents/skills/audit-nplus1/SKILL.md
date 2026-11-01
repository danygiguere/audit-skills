---
name: audit-nplus1
description: Query-amplification (N+1) checklist. Use when code loads related data inside a loop over a collection, or when reviewing ORM-heavy read paths for performance.
---

Read `../audit/references/operability/nplus1.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
