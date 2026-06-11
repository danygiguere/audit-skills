---
name: audit-state-management
description: Shared and concurrent state checklist. Use when reviewing code with shared mutable state, caching, counters, or check-then-act sequences (race conditions).
---

Read `../audit/references/correctness/state-management.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each finding
against surrounding code before reporting. Report findings with severity and
file:line references.
