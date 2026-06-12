---
name: audit-crypto
description: Cryptography and data-protection checklist. Use when code hashes passwords, encrypts data, generates tokens or randomness, or compares secrets.
---

Read `../audit/references/access-data-security/crypto-data-protection.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
