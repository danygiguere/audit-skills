---
name: audit-resource-limits
description: Resource-exhaustion checklist. Use when reviewing endpoints for missing pagination, unbounded loops over input, missing size or rate limits, regex backtracking, or IN lists and bulk statements that can exceed database parameter limits.
---

Read `../audit/references/operability/resource-limits.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
