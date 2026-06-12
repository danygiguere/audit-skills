---
name: audit-statelessness
description: Statelessness checklist for horizontally scaled apps. Use when reviewing services meant to run as multiple replicas — in-memory sessions or counters, module/static mutable state, local-disk uploads, process-local locks or schedulers, sticky-session assumptions, state lost on deploy.
---

Read `../audit/references/operability/statelessness.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
