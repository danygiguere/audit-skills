---
name: audit-config
description: Insecure-configuration checklist. Use when reviewing app config, CORS, security headers, debug flags, cookies, or environment-specific settings.
---

Read `../audit/references/input-api-dependency/config.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
