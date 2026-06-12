# Mass Assignment

## Invariant

Request data is never bound wholesale onto persistence objects. Every site
where request input hydrates a model has an explicit **allowlist** of
writable fields, chosen for that context — what a user may set on their own
profile is not what an admin endpoint may set, and neither is "every column
the model has."

## Does not apply when

- Binding goes through explicit DTOs or structs containing only safe fields,
  mapped field-by-field onto the model (idiomatic in Go, Rust, and strict
  Java codebases) — there the type itself is the allowlist. Verify the DTO
  doesn't simply mirror the entire model.

## Why it happens

ORMs make whole-payload hydration a one-liner, and the dangerous and safe
versions look almost identical at the call site. Denylists ("block these
three fields") feel equivalent to allowlists but rot: every column added
later is writable by default. And the failure is invisible in testing —
the UI never sends the malicious field, so nothing exercises the hole until
someone crafts a request by hand.

## Detection smells

- A handler passing the entire parsed request body into a create, update,
  or fill operation on a model.
- Protection expressed as a denylist (guarded/excluded fields) rather than
  an allowlist — new columns are writable the day they're added.
- One shared allowlist serving multiple contexts: self-service profile
  update, admin edit, and registration all permitting the same fields.
- Sensitive fields in an allowlist "because the UI never sends them" —
  role, owner/tenant foreign keys, balances, verification flags.
- Nested or relation parameters bound through the parent (the payload can
  create or repoint associated records the endpoint never intended).
- A sensitive column added to a model whose binding sites were written long
  before it existed and never revisited.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the allowlist usually lives                                                                                                                  |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | strong parameters: `params.require(:user).permit(:name, :email)`; `permit!` is the smell                                                           |
| Laravel      | `$fillable` (allowlist) vs `$guarded` (denylist — weaker); `$request->validated()` into `update()`                                                 |
| Django       | `ModelForm`/DRF serializer with explicit `fields = [...]`; `fields = "__all__"` is the smell                                                       |
| Spring       | dedicated request DTOs mapped to entities; binding `@ModelAttribute` straight onto an entity is the smell                                          |
| Node/Express | `Object.assign(model, req.body)` / spread into create is the smell; pick explicit fields; Mongoose `strict`, Sequelize `fields:`                   |
| Vapor        | decode into a dedicated `Content` DTO (the type is the allowlist); `req.content.decode(User.self)` straight into the Fluent model is the smell     |
| .NET         | known as **overposting**: bind to DTOs/records or `TryUpdateModelAsync` with included properties; binding EF entities directly is the smell        |
| Go           | mostly N/A (see guard) — request structs are the allowlist; the smell is binding into the DB model struct itself (`c.Bind(&user)` on a GORM model) |

## Example

Vulnerable shape:

```text
handler update_profile(request):
    user = current_principal()
    user.update(request.body)        # payload may contain role: "admin",
    respond 200                      # owner_id, balance, is_verified ...
```

Fixed shape — the allowlist is explicit, local to this context, and
everything else in the payload is ignored:

```text
handler update_profile(request):
    user = current_principal()
    user.update(pick(request.body, ["name", "email", "avatar_url"]))
    respond 200
```

## Severity guidance

- **Critical** — privilege or financial fields are bindable: role/admin
  flags, balances, prices, verification status, or owner/tenant foreign
  keys (repointing ownership is also an `authorization.md` finding).
- **High** — bindable fields that corrupt business state (statuses,
  quotas, timestamps the system relies on).
- **Medium** — a denylist or over-broad allowlist with no currently
  sensitive field exposed — it's a time bomb, not a present breach.
- Boundary validation that strips unknown fields upstream lowers severity
  one level but does not close the finding (see
  `../input-api-dependency/api-contract-validation.md`) — the binding site
  itself must still be explicit.
