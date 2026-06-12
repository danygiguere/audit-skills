# Injection

## Invariant

Every query, shell command, template, and path that incorporates input —
from the request, a stored record, a file, or another service — is built
through a parameterization or escaping API, never by concatenating or
interpolating the input into the executable string. Where parameterization
is impossible (identifiers, structural fragments), the value is matched
against a server-defined allowlist.

## Does not apply when

- The interpolated value is a server-side constant or enum that no input
  can influence on any path.

## Why it happens

String building is the path of least resistance: concatenation works in
every language and reads naturally. Developers sanitize the obvious request
parameter but miss values that arrive indirectly — headers, stored rows,
queue payloads — because "it came from our database" feels trusted. ORMs
create false safety: the safe API sits next to a raw-query escape hatch,
and dynamic requirements (sorting, filtering, search) push code through it.

## Detection smells

- A query, command, template, or path string assembled with concatenation,
  interpolation, or format calls where any operand traces back to input.
- A shell executed as one interpolated string instead of a program name plus
  an argument array (the array form never invokes a shell parser).
- An ORM's raw/native query method receiving a string built from variables
  rather than a fixed string with bound placeholders.
- Sort column, direction, table name, or field list taken from the request
  and spliced into the query — placeholders cannot cover identifiers, so
  absence of an allowlist here is the finding.
- User input used **as** a template (passed to the template engine for
  evaluation) rather than as data rendered **into** a template.
- A value read from the database or a queue and used in a later query or
  command without parameterization — second-order injection; storage is not
  sanitization.
- NoSQL queries whose filter objects are built directly from request bodies,
  letting callers smuggle operators (`{"$ne": null}`-shaped values).
- A function that builds a query, command, or path from input and returns
  it instead of executing it — the sink lives in a caller; find the call
  sites before concluding it is safe.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Safe primitive vs the trap                                                                                                     |
|--------------|--------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `where("x = ?", v)` vs `where("x = #{v}")`; `system("cmd", arg)` vs backticks                                                  |
| Laravel      | bindings in `whereRaw('x = ?', [v])` vs interpolated `DB::raw`; `Process` arrays                                               |
| Django       | queryset params / `cursor.execute(sql, [v])` vs f-string SQL; `subprocess` lists                                               |
| Spring       | `PreparedStatement` / JPA named params vs string-built JPQL; `ProcessBuilder`                                                  |
| Node/Express | placeholder queries (`?`/`$1`) vs template-literal SQL; `execFile` vs `exec`                                                   |
| Vapor        | Fluent parameterizes; raw SQL via SQLKit `\(bind:)` interpolation — assembling `SQLQueryString` from raw input is the smell    |
| .NET         | EF parameterizes; `FromSqlInterpolated` is safe — `FromSqlRaw` with string concatenation is the smell; Dapper named parameters |
| Go           | `database/sql` placeholders (`$1`/`?`); `fmt.Sprintf` into a query or `exec.Command("sh", "-c", s)` is the smell               |

## Example

Vulnerable shape:

```text
handler search(request):
    sql = "SELECT * FROM orders WHERE status = '" + request.query.status +
          "' ORDER BY " + request.query.sort          # both injectable
    db.raw(sql)
    shell.run("convert " + request.query.file + " out.png")
```

Fixed shape — data goes through placeholders, identifiers through an
allowlist, commands through argument arrays:

```text
SORTABLE = {"created_at", "total", "status"}

handler search(request):
    sort = request.query.sort
    if sort not in SORTABLE: respond 422
    db.query("SELECT * FROM orders WHERE status = ? ORDER BY " + sort,
             [request.query.status])                  # value bound, id allowlisted
    shell.run_argv(["convert", request.query.file, "out.png"])
```

## Severity guidance

- **Critical** — SQL/NoSQL injection reaching data reads or writes, command
  injection, or template injection with code execution.
- **High** — injection constrained to a narrow surface (single column,
  blind/boolean-only extraction) or second-order paths requiring a prior
  write.
- **Medium** — identifier injection limited to columns of one table, or
  injection into a query the caller could already fully control.
- Reachability matters: an injectable sink behind an admin-only path drops
  one level; one reachable pre-auth rises one.
