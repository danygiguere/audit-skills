# Authorization

## Invariant

Every state-changing or sensitive action is permission-checked server-side,
at the point where the action executes. A check that lives only in the UI,
the client, or the routing layer is a usability feature, not access control.
Authentication answers *who*; authorization answers *may they* — both must
hold before the action runs.

## Does not apply when

- The action is genuinely public (intended for any visitor) and touches no
  state belonging to another principal.

## Why it happens

Authorization gets added where it is first noticed — a hidden button, a
route group — and developers assume coverage propagates. Route middleware
confirms "logged in" and that reads as "allowed". New endpoints added inside
an authenticated group inherit authentication but not authorization. When
checks are opt-in calls rather than a deny-by-default layer, every forgotten
call site is silently open, and nothing fails loudly when one is missing.

## Detection smells

- A mutation handler whose only gate is "caller is authenticated" — no role,
  permission, or ownership comparison in its body or middleware chain.
- The check exists on the read/list path but is absent on the sibling
  create, update, or delete path.
- Access expressed only by hiding UI elements or omitting links; the
  endpoint itself accepts any caller (vertical escalation by URL).
- Admin endpoints protected by obscurity — an unlinked path, a non-obvious
  route name, or a frontend route guard.
- Permission checks are per-handler calls with no enforcement that they ran;
  handlers in the same module exist both with and without the call.
- Role or privilege values read from the request (body fields, client-set
  claims) instead of server-side state — including `role`/`is_admin`/
  `owner_id` reachable through a generic update (mass assignment).
- Horizontal checks missing while vertical ones exist: the role is verified
  but not that the target resource belongs to the caller.
- A guard added to one branch, handler, or layer but not its siblings —
  enumerate every peer path that touches the same resource (other branches,
  early returns, error paths, sibling handlers); any without an equivalent
  check is the finding.
- The gate and the action disagree on the target: the check reads one
  request field (the parent ID, the URL segment) while the operation picks
  its target from another (a name or ID in the body) — the gate is
  bypassable.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the check usually lives                                                                                                                                                 |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | Pundit `authorize`/`policy_scope` (+ `verify_authorized` for deny-by-default); CanCanCan                                                                                      |
| Laravel      | policies and gates; `$this->authorize(...)` in controllers/FormRequests; `can:` middleware                                                                                    |
| Django       | DRF `permission_classes` + `has_object_permission`; `@permission_required`                                                                                                    |
| Spring       | `@PreAuthorize` method security; `SecurityFilterChain` rules (URL rules alone are route-layer only)                                                                           |
| Node/Express | per-route middleware (`requireRole(...)`) plus in-handler object checks; nothing is implicit                                                                                  |
| Vapor        | `req.auth.require(User.self)` + explicit ownership checks in handlers; `GuardMiddleware` on route groups — no built-in policy layer                                           |
| .NET         | `[Authorize]` + policy-based authorization; resource checks via `IAuthorizationService.AuthorizeAsync(user, resource, policy)` — route-level `[Authorize]` alone is the smell |
| Go           | authn in middleware (chi/gin), ownership checks explicit per handler — no framework policy layer; casbin where central policies are needed                                    |

## Example

Vulnerable shape — the router requires login, nothing requires permission:

```text
handler delete_article(request):
    # router: "authenticated users only"
    article = db.articles.find(request.params.id)
    article.delete()                    # any logged-in user deletes anything
```

Fixed shape — an explicit permission decision at the point of action,
covering both role (vertical) and ownership (horizontal):

```text
handler delete_article(request):
    article = db.articles.find(request.params.id)
    require permission(request.principal, "delete", article)
        # denies unless principal owns it or holds the moderator role
    article.delete()
```

## Severity guidance

- **Critical** — vertical escalation: any user can perform admin operations,
  grant roles, or change permissions.
- **High** — horizontal escalation on writes: mutating data or triggering
  actions on behalf of other principals.
- **Medium** — missing check on a low-impact action, or a check enforced at
  the wrong layer with a compensating server-side control.
- UI-only gating carries the full severity of the action it hides — the
  hidden button is not a mitigating factor.

## Remediation

See `../remediation/authz-patterns.md` — deny-by-default enforcement,
policy objects, and checks placed at the point of action.
