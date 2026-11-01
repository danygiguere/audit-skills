---
name: audit-injection
description: Injection audit checklist (SQL, NoSQL, command, template, path). Use when queries, shell commands, templates, or paths are built from user input.
---

Read `../audit/references/input-api-dependency/injection.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
