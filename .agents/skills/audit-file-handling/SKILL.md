---
name: audit-file-handling
description: File upload/download safety checklist. Use when code accepts, stores, processes, or serves files — path traversal, type and size limits, storage location.
---

Read `../audit/references/input-api-dependency/file-handling.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
