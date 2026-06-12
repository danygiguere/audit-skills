---
name: audit-output-encoding
description: Output encoding and XSS checklist. Use when user-controlled data is rendered into HTML, JavaScript, CSS, URLs, headers, or emails.
---

Read `../audit/references/access-data-security/output-encoding.md` and apply its checklist to the code the
user specified (or the current diff if none was given). Verify each candidate
with `../audit/references/methodology/verify.md` before reporting. Report findings with severity and
file:line references.
