---
name: audit-parser-differentials
description: Parser/validator differential checklist. Use when reviewing validators, regexes, allowlists, URL or path parsing, content-type checks, or normalization — inputs a gate accepts but the downstream consumer interprets differently (unanchored regexes, startswith allowlists, two URL parsers, validate-then-reparse).
---

Read `../audit/references/input-api-dependency/parser-differentials.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
