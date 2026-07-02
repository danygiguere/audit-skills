# Scoping & Coverage (methodology)

Loaded at the identify step when the audit target is **larger than a
diff** — a module, service, or whole repository. `verify.md` protects
precision; this file protects recall. The failure mode it prevents:
skimming files in directory order, grepping for scary words, and calling
the result "an audit of the repo".

## Procedure

1. **Inventory entry points before reading any code.** Enumerate where
   untrusted input or scheduled work enters: HTTP routes and controllers,
   webhook receivers, queue/stream consumers, scheduled jobs, CLI commands
   fed by external data, file-upload and websocket handlers. Use the
   framework's own routing artifacts (route tables, controller
   directories, job registries) so the inventory is complete rather than
   sampled.
2. **Rank by exposure, not by file order.** Highest first:
   unauthenticated surfaces; then cross-tenant/cross-user surfaces; then
   authenticated own-data; then admin/internal; dev-only last. Within a
   rank, anything touching money, credentials, PII, or destructive
   operations moves to the front.
3. **Declare a budget.** Say how many entry points this pass will cover in
   full — "all 12 routes" or "the top 5 by exposure" — before starting.
   A declared partial pass beats an implied complete one.
4. **Audit depth-first per entry point.** Follow each chosen entry point
   end to end — handler → validation → service → query → template/response
   → side effects (jobs, emails, external calls) — applying the router
   table's matching checklists as each behavior appears. Read the files on
   the path in full. Do not breadth-first skim every file at one layer.
5. **Verify and report as usual** (`verify.md`, `severity.md`), then close
   with a coverage statement.

## Coverage statement

Every scoped audit ends by naming, explicitly:

- which entry points were audited end to end, against which checklists;
- which were **not** examined (the rest of the inventory from step 1), and
  what the next pass should take by the same exposure ranking;
- any code reachable only outside the inventory (libraries, shared
  utilities) that was read incidentally, so partial knowledge is not
  mistaken for coverage.

Findings from a partial pass are real findings — report them; a partial
pass is only a problem when it is presented as a full one.

## Anti-patterns

- Grepping for `password|secret|eval` and reporting the hits as the audit.
- Reading files alphabetically or by size until time runs out.
- "Audited the service" after reading three files — `verify.md`'s coverage
  honesty applies to scope claims too.
- Spending the whole budget on the first entry point encountered rather
  than the highest-exposure one.
