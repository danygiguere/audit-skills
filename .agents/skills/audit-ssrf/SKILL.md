---
name: audit-ssrf
description: Server-side request forgery checklist (includes open redirects). Use when code makes network requests to URLs, hosts, or IPs derived from user input — webhooks, fetchers, URL previews, importers.
---

Read `../audit/references/input-api-dependency/ssrf.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
