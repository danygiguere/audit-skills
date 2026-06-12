---
name: audit-api-validation
description: Input validation and API contract checklist. Use when reviewing request validation, DTOs, public endpoints, types, bounds, or unknown-field handling.
---

Read `../audit/references/input-api-dependency/api-contract-validation.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
