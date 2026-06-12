# Data Exposure

## Invariant

Every response, error message, and log line contains only the fields
explicitly intended for that consumer. Serialization is an allowlist
decision made per endpoint and per audience; "the UI doesn't display it" is
not a control, because the wire carries whatever the server sends.

## Why it happens

Serializers default to everything — returning the model object is one line,
declaring the field list is many. Columns added later (hashes, tokens,
internal flags) silently join every existing response. Error detail meant
for development reaches production because rendering differs only by a
config flag. Logs accrete: whole request bodies and objects get dumped while
debugging and never get removed, then fan out to log aggregators, alerts,
and third-party tooling.

## Detection smells

- A handler returns the model/record object directly (or via its default
  to-JSON) instead of an explicit field list or response type.
- Field selection is "all columns minus a denylist" — any new sensitive
  column is exposed by default until someone remembers to hide it.
- The response carries fields no client ever reads; what the UI renders is a
  strict subset of what the JSON ships.
- The error handler interpolates the exception into the response: stack
  traces, SQL fragments, file paths, or framework versions reach the client.
- Log statements dump entire request bodies, sensitive headers
  (authorization, cookies), or whole model objects rather than chosen fields.
- One serializer serves every audience — the admin view and the public view
  return the same shape.
- Validation or not-found errors echo internal identifiers, table or column
  names, or absolute filesystem paths.
- A new field, enum value, or data class added without updating the
  registries keyed on its kind — redaction sets, sanitizer field lists,
  serializer allowlists; a new sensitive entity silently misses every
  protection enumerated before it existed.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where field selection usually lives                                                                                             |
|--------------|---------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `as_json(only:)`, serializer classes/jbuilder vs raw `render json: model`; `filter_parameters` for logs                         |
| Laravel      | API Resources vs returning the model; `$hidden`/`$visible` are denylists; `APP_DEBUG=false`                                     |
| Django       | DRF serializer `fields = [...]` (not `__all__`); `DEBUG=False`; `sensitive_post_parameters`                                     |
| Spring       | DTOs vs serialized entities; `@JsonIgnore` is a denylist; `server.error.include-stacktrace=never`                               |
| Node/Express | hand-built response objects vs `res.json(model)`; error middleware hiding `err.stack`; pino/winston redaction                   |
| Vapor        | return dedicated `Content` response DTOs, never Fluent models directly; `ErrorMiddleware` controls error detail per environment |
| .NET         | return DTOs/records, never EF entities; `ProblemDetails` for errors; `UseDeveloperExceptionPage` only in Development            |
| Go           | response structs with explicit json tags, `json:"-"` on sensitive fields; never marshal DB structs wholesale                    |

## Example

Vulnerable shape:

```text
handler get_profile(request):
    user = db.users.find(request.params.id)
    respond json(user)         # ships password_hash, reset_token, email,
                               # is_admin — every column, forever
```

Fixed shape — an explicit allowlist per consumer:

```text
handler get_profile(request):
    user = db.users.find(request.params.id)
    respond json({
        id:   user.id,
        name: user.name,
        bio:  user.bio })      # new columns stay private until chosen
```

## Severity guidance

- **Critical** — credentials, password hashes, API keys, or session/reset
  tokens present in responses or logs.
- **High** — PII (emails in bulk, addresses, government IDs,
  financial/health data) exposed beyond its intended audience; production
  error responses revealing exploitable structure (SQL, paths, traces).
- **Medium** — internal IDs, versions, paths, or low-sensitivity hidden
  fields leaking; verbose logging without secrets.
- Exposure in logs is not less severe than in responses — logs reach more
  systems and more people, and persist longer.
