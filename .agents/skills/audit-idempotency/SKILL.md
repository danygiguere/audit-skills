---
name: audit-idempotency
description: Safe-retry and duplicate-delivery checklist. Use when reviewing payments, webhooks, queue consumers, emails, or any handler that may execute twice.
---

Read `../audit/references/correctness/idempotency.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
