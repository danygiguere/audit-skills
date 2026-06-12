---
name: audit-blocking-io-async
description: Blocking I/O in async contexts checklist. Use when reviewing async/await code, event-loop or reactor-based services, coroutines, or worker/thread pools — sync calls in async handlers, CPU work on the event loop, sync-over-async, blocking sleeps, missing timeouts.
---

Read `../audit/references/operability/blocking-io-async.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
