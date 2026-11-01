---
name: audit-caching
description: Caching correctness checklist. Use when reviewing caches — keys missing a user/tenant dimension, stale data after writes, cache stampede, cached errors, or per-user responses landing in a shared or CDN cache.
---

Read `../audit/references/operability/caching.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
