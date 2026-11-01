---
name: audit-deserialization
description: Insecure deserialization checklist. Use when untrusted bytes (request bodies, cookies, sessions, cache entries, queue messages, uploaded files) are deserialized — native object deserializers, polymorphic JSON/XML typing, unsafe YAML, or missing type allowlists.
---

Read `../audit/references/input-api-dependency/deserialization.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
