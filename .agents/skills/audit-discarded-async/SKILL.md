---
name: audit-discarded-async
description: Discarded async work checklist (fire-and-forget). Use when reviewing code that creates promises, futures, tasks, or reactive publishers (Mono/Flux) — results not awaited, returned, or composed; bare subscribe; floating promises; async writes that silently never run.
---

Read `../audit/references/correctness/discarded-async.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
