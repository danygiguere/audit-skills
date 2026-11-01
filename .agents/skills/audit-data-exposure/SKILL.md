---
name: audit-data-exposure
description: Data over-exposure checklist. Use when reviewing API responses, serializers, error messages, or logs for leaked fields, PII, or internal details.
---

Read `../audit/references/access-data-security/data-exposure.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
