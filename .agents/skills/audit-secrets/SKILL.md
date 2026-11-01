---
name: audit-secrets
description: Secrets-handling checklist. Use when reviewing code or config touching API keys, credentials, or tokens — hardcoding, logging, committing, rotation.
---

Read `../audit/references/input-api-dependency/secrets.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
