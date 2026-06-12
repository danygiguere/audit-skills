# Insecure Direct Object Reference (IDOR)

## Invariant

Every resource looked up or mutated using an identifier taken from the
request — ID, UUID, slug, filename, foreign key — must be verified as owned
by, or visible to, the current principal before the operation proceeds.
Possession of a valid identifier is never proof of authorization.

## Does not apply when

- The resource is genuinely public (read-only, intended for any visitor).
- The identifier comes from server-side session state, not from the request.

## Why it happens

ORMs make find-by-id a one-liner; the ownership check is a second line that
is easy to omit and invisible when missing. Authentication middleware
confirms *who* the caller is, and developers conflate that with *what* they
may touch. Unguessable IDs (UUIDs) create false comfort — they leak through
logs, URLs, exports, and other users' clients, and enumeration is not the
only way to obtain one.

## Detection smells

- A handler reads an identifier from the path, query, or body, fetches the
  resource, and returns or mutates it without comparing its owner/tenant to
  the current principal.
- The ownership check exists on the read endpoint but not on its sibling
  update or delete endpoint.
- The list endpoint scopes its query to the current user, but the detail
  endpoint fetches by ID alone.
- Bulk operations accept a list of IDs and process them without a per-ID
  authorization check.
- Nested resources: the child is fetched by its own ID without verifying it
  belongs to the parent in the URL (`/projects/1/tasks/99` returning task 99
  from project 2).
- Webhook or job handlers trust resource IDs arriving in external payloads.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the check usually lives                                                                                               |
|--------------|-----------------------------------------------------------------------------------------------------------------------------|
| Rails        | `current_user.posts.find(id)` vs `Post.find(id)`; Pundit/CanCanCan policies                                                 |
| Laravel      | scoped route-model binding; policies (`$this->authorize('update', $post)`)                                                  |
| Django       | `get_object_or_404(Post, pk=pk, owner=request.user)`; queryset scoping in DRF                                               |
| Spring       | `findByIdAndOwner(id, principal)`; `@PreAuthorize` with object checks                                                       |
| Node/Express | a `WHERE owner_id = ?` clause or explicit `if (post.ownerId !== req.user.id)`                                               |
| Vapor        | `Todo.query(on: req.db).filter(\.$owner.$id == user.id)` vs bare `Todo.find(id, on: req.db)`                                |
| .NET         | EF Core `Where(x => x.OwnerId == userId && x.Id == id)` vs bare `FindAsync(id)`; resource-based authorization handlers      |
| Go           | ownership in the query itself: `WHERE id = $1 AND owner_id = $2`; GORM `Where("owner_id = ?", uid)` vs bare `First(&t, id)` |

## Example

Vulnerable shape:

```text
handler update_invoice(request):
    invoice = db.invoices.find(request.params.id)   # any valid ID works
    invoice.update(request.body)
```

Fixed shape — the lookup itself is scoped, so an unauthorized ID behaves
exactly like a nonexistent one (404, not 403, to avoid confirming existence):

```text
handler update_invoice(request):
    invoice = db.invoices.find_where(
        id    = request.params.id,
        owner = request.principal.id)               # scope IS the check
    if invoice is null: respond 404
    invoice.update(request.body)
```

## Severity guidance

- **Critical** — write or delete access to other principals' data, or read
  access to credentials/financial/health data.
- **High** — read access to other principals' private data.
- **Medium** — read access to low-sensitivity data, or exposure limited to
  resource existence/metadata.
- Easy enumeration (sequential IDs) raises severity one level; unguessable
  IDs do **not** lower it below medium — they are obscurity, not access
  control.

## Remediation

See `../remediation/authz-patterns.md` — ownership-scoped queries, policy
objects, and scoped route binding.
