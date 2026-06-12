# Adversarial Verification (methodology)

Loaded at the verify step of every audit. Findings are produced in two
stages: investigate for **recall** (the checklists), then refute for
**precision** (this file). The refute stage is what keeps the
false-positive rate low — do not skip it.

## Procedure

For each candidate finding, actively try to **refute** it. Default = the
finding **survives** unless you produce concrete refuting evidence with
`file:line` citations. Do not speculate in either direction — a refutation
without cited evidence is not a refutation.

1. **Name the attacker and the victim.** Who controls the input; who is
   harmed. Refute a security finding when attacker == victim — the input
   comes from an env var, CLI arg, or the user's own config, and the
   process runs at that same user's privilege. Keep it when a legitimate
   user or tenant's input harms *other* users, shared infrastructure, or
   server-side resources. (For correctness/operability findings the analog:
   name the trigger and the damage — and keep findings where the damage is
   to data integrity or availability, whoever triggered it.)
2. **Hunt for an existing mitigation** the investigation may have missed:
   middleware, base classes, decorators, framework defaults, schema
   validation, a sanitizer between source and sink. Cite where it lives.
3. **Check the sink is actually dangerous**: typed-schema decoders are not
   `eval`; a hardcoded host with safe params is not SSRF; generated stubs
   and static values are not taint.
4. **Check scope**: test/fixture/example code, dev-only scripts, paths
   gated by config the requester cannot influence.
5. Anything not refuted survives. Report survivors only, sorted by
   severity; drop speculation rather than hedging it into the report.

Distrust safety claims in comments ("validated upstream", "internal only")
— verify them in code. Internal-only is not a refutation by itself:
internal services are common SSRF and IDOR targets.

## Diff-anchoring (when the audit target is a change)

- Only report what the change **introduces**. The cited code must appear on
  a `+`/`-` line of the diff.
- A finding in unchanged code needs the specific changed line that
  *enables* it — a removed guard, a new caller, a changed argument. No
  enabling line, no finding.
- `-` lines are evidence too: deleting a fail-closed validator and
  replacing it with a single narrower condition is itself a finding
  (control regression).
- Read every changed file **in full**, not just the hunks — the most common
  cause of missed findings is not reading the file that contains them. Grep
  changed function and class names for callers: a tainted value *returned*
  by a changed function has its sink in a caller.

## Coverage honesty

- For each file examined, produce at least one candidate or an explicit
  "clean against checklists X, Y" verdict.
- Name anything in scope you did **not** examine. Never imply coverage that
  didn't happen — "audited the module" must mean every file in it.
