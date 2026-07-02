---
name: audit-dependencies
description: Dependency and supply-chain checklist. Use when a change adds or updates packages, lockfiles, registries, or install tooling — unpinned versions, missing lockfile updates, install scripts, typosquats, dependency confusion, abandoned or vulnerable packages.
---

Read `../audit/references/input-api-dependency/dependencies.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
