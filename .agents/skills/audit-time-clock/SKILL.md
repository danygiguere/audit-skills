---
name: audit-time-clock
description: Time, timezone, and clock-correctness checklist. Use when code stores or computes timestamps, durations, timeouts, or expiry — naive vs aware datetimes, server-local now(), wall-clock for elapsed time, DST and calendar math, cross-zone comparisons.
---

Read `../audit/references/correctness/time-clock.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
