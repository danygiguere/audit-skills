# Authorization fixes (remediation patterns)

## Scope

Fix patterns for confirmed findings from
`../access-data-security/authorization.md`,
`../access-data-security/idor.md`, and
`../access-data-security/tenant-isolation.md` — missing permission checks,
resources fetched by request-supplied ID without ownership verification, and
queries unscoped by tenant. All four patterns restore the same invariant: a
valid identifier is never authorization; access is decided server-side at the
point of action.

## Patterns

### 1. Ownership/tenant-scoped query

**When to use:** a handler fetches a resource by ID from the request and the
resource has a clear owner or tenant column. The default fix for IDOR and
tenant-isolation findings.

```text
# before: find by ID, check (maybe) afterwards
resource = db.resources.find(request.params.id)

# after: the scope IS the check
resource = db.resources.find_where(
    id     = request.params.id,
    owner  = request.principal.id)      # or tenant = principal.tenant_id
if resource is null: respond 404        # 404, not 403 — do not confirm existence
```

Trade-off: the check is invisible in the handler body, so it must be the
codebase-wide convention — a single unscoped `find` reopens the hole.

### 2. Centralized policy object

**When to use:** the permission rule is more than ownership (roles, states,
shared access), or the same rule is duplicated across several handlers. One
place answers "may this principal do X to Y".

```text
policy ResourcePolicy:
    can_update(principal, resource):
        return resource.owner == principal.id
            or principal.has_role("admin", resource.tenant)

handler update_resource(request):
    resource = fetch_scoped(request)            # pattern 1 still applies
    authorize(ResourcePolicy.can_update, request.principal, resource)  # raises 403/404
    resource.update(validated_input)
```

Trade-off: an extra indirection per action; worth it once a rule has two
call sites or two conditions.

### 3. Scoped route binding

**When to use:** nested resources (`/projects/:pid/tasks/:tid`) or frameworks
that auto-resolve route parameters to records. Resolve every resource through
the principal's (or parent's) relation so an out-of-scope ID can never bind.

```text
resolve(request):
    project = request.principal.projects.find(request.params.pid)   # 404 if not theirs
    task    = project.tasks.find(request.params.tid)                # 404 if wrong parent
```

Trade-off: pushes authorization into routing/binding configuration — handlers
get simpler, but reviewers must know bindings carry the check.

### 4. Deny-by-default middleware

**When to use:** audits keep finding individual unprotected routes — fix the
class, not the instance. Every route must declare its permission explicitly;
an undeclared route is rejected, not silently allowed.

```text
middleware authorize_route(request):
    rule = route_permissions.get(request.route)
    if rule is null: respond 500 "route has no permission declaration"   # fail closed
    if not rule.allows(request.principal): respond 403
```

Trade-off: requires touching every route once at adoption; after that, new
endpoints cannot ship unchecked.

## Ecosystem glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Native form of these patterns                                                                                                                                 |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `current_user.resources.find(id)`; Pundit policies + `verify_authorized` for deny-by-default                                                                  |
| Laravel      | scoped route-model binding (`->scopeBindings()`); policies + `authorize()`; global query scopes                                                               |
| Django       | `get_object_or_404(Model, pk=pk, owner=request.user)`; DRF `get_queryset` scoping + permission classes                                                        |
| Spring       | `findByIdAndOwner(id, principal)` repository methods; `@PreAuthorize`; deny-all default in security config                                                    |
| Node/Express | `WHERE owner_id = ?` in the query layer; CASL/policy modules; a router-level auth middleware applied before all routes                                        |
| Vapor        | ownership-scoped Fluent queries; `req.auth.require` + guard middleware; policies live in the service layer (no framework construct)                           |
| .NET         | resource-based authorization handlers via `IAuthorizationService`; EF global query filters for ownership/tenant scoping; `FallbackPolicy` for deny-by-default |
| Go           | ownership in the WHERE clause; central authorize helpers or casbin; deny-by-default routing middleware                                                        |

## Applying fixes

- Make the smallest change that restores the invariant: scope the one query or
  add the one policy call; do not redesign the authorization layer to fix a
  single endpoint.
- Match the surrounding code's existing convention — if the codebase uses
  policies, add a policy method; do not introduce a second mechanism.
- Add or extend a test proving the fix: a request for another principal's
  resource ID must return 404 (or 403 where the convention is explicit denial).
- Never mix the fix with unrelated refactoring; the diff should read as
  "authorization added", nothing else.
