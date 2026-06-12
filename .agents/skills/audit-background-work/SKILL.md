---
name: audit-background-work
description: Background job and queue checklist. Use when reviewing async jobs, scheduled tasks, or consumers — retries, poison messages, ordering, timeouts.
---

Read `../audit/references/correctness/background-work.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
