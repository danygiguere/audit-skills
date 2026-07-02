# Severity Rubric (methodology)

Loaded at the report step of every audit. Each checklist's own *Severity
guidance* instantiates this scale for its domain and wins on domain
specifics; this file defines what the levels mean so a High from one
checklist equals a High from another.

## The scale

- **Critical** — an attacker-triggerable path to full compromise of
  another principal's account, money, or data; code execution on the
  server; or certain data corruption/loss in normal operation. No
  meaningful precondition the attacker doesn't control. Fix before merge
  or ship a mitigation the same day.
- **High** — the same classes of impact but gated by a real precondition
  (authentication as any user, a specific but common configuration, a
  race window), limited to one principal per exploitation, or an
  operability defect that causes an outage under realistic load or a
  correctness bug that silently corrupts data over time.
- **Medium** — bounded blast radius: metadata or existence leaks,
  self-inflicted-only harm, a missing defense-in-depth layer whose primary
  control exists, correctness bugs whose damage is visible and recoverable.
- **Low** — hygiene with no current path to harm: works today but fragile
  against likely change; hardening notes. Report briefly; never pad a
  report with Lows to look thorough.

## Assigning a level

1. Start from **impact**: what does the attacker gain, or what breaks, in
   the worst plausible case — not the worst imaginable one.
2. Adjust for **exploitability**, never by averaging:
   - Reachable pre-auth, or by any tenant against another: **raise** one
     level.
   - Requires privileges that already imply the impact (an admin harming
     what admins administer): **cap at Medium** — likely a non-finding;
     re-run the attacker/victim test in `verify.md`.
   - Attacker == victim (harms only the requester): **cap at Medium**.
   - Test/dev/example scope with no production data or credentials: **cap
     at Low**.
   - Easy discovery (sequential IDs, error messages that guide, a public
     endpoint list) raises; obscurity (unguessable IDs, internal-only
     paths) never lowers below **Medium** — it is not a control.
3. One severity per finding, chosen for the finding's *primary* impact.
   If two levels genuinely remain, state the single condition that decides
   between them ("High if the bucket is shared across tenants, else
   Medium") rather than hedging.

## Reporting

Sort findings by severity, Critical first. Within a level, sort by
confidence. A severity claim inherits the evidence rules of `verify.md`:
the impact must be demonstrable from cited code, not narrated.
