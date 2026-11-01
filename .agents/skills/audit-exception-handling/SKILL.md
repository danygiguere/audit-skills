---
name: audit-exception-handling
description: Exception and error-handling audit checklist. Use when reviewing try/catch blocks, error propagation, empty or overly broad catches, rethrowing, cleanup/finally paths, async error handling, or whether errors map to the right HTTP status (404 vs 403, 401, 422, 409).
---

Read `../audit/references/correctness/exception-handling.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
