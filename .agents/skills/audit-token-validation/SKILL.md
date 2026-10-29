---
name: audit-token-validation
description: Inbound token and webhook verification checklist. Use when code verifies JWTs, API keys, signed URLs, or webhook signatures — decode-without-verify, alg confusion, missing exp/aud/iss checks, kid/JWKS handling, HMAC over raw body, replay windows.
disable-model-invocation: true
---

Read `../audit/references/access-data-security/token-validation.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
