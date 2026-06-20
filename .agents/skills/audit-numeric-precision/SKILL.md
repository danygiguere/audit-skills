---
name: audit-numeric-precision
description: Numeric and money precision checklist. Use when code computes money, totals, taxes, or splits — float used for currency, ad hoc rounding, integer overflow, division remainders, or unit/currency mismatches.
---

Read `../audit/references/correctness/numeric-precision.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
