# Cross-Site Request Forgery (CSRF)

## Invariant

Every state-changing endpoint whose authentication is attached automatically
by the browser — session cookies, Basic auth, client certificates — must
verify that the request originated from the application itself: a CSRF token
or a validated Origin/Sec-Fetch-Site check. Browsers send cookies on
cross-site requests; an authenticated request proves identity, not intent.

## Does not apply when

- Authentication is purely via an Authorization header token (bearer, JWT,
  API key) that the browser never attaches automatically — but confirm the
  server does not *also* accept the same credential from a cookie.
- The endpoint changes no state (safe, idempotent reads) — cross-site
  callers cannot read the response anyway.

## Why it happens

Framework CSRF middleware is opt-out per route, and exemptions added for
webhooks or "API" route groups widen over time until cookie-authenticated
endpoints sit inside them. Mutations implemented as GET escape protection
entirely, because frameworks only guard unsafe methods. SameSite cookie
defaults create false confidence: `Lax` still sends cookies on top-level
navigations, client behavior varies, and a subdomain or sibling-site bug
bypasses it.

## Detection smells

- CSRF middleware disabled globally or exempted for route groups that still
  use cookie sessions — most commonly `/api/*` consumed by the same browser
  app with cookies.
- Endpoints that mutate state (delete, toggle, transfer, role change)
  reachable via GET or HEAD.
- A cookie-authenticated mutation handler with no token verification in its
  middleware chain and no Origin/Referer validation.
- The token is rendered into forms but never validated server-side —
  verification stubbed, commented out, or exempted.
- Dual-auth endpoints accepting either a header token or a session cookie,
  with CSRF skipped because "it's a token API".
- Protection asserted to be `SameSite` alone, with no token or origin check
  as the primary control.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where protection usually lives                                                                                                                 |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `protect_from_forgery` (default); risk: `skip_before_action :verify_authenticity_token`                                                        |
| Laravel      | `VerifyCsrfToken` middleware + `@csrf` directive; risk: routes in the `$except` array                                                          |
| Django       | `CsrfViewMiddleware` + `{% csrf_token %}`; risk: `@csrf_exempt`                                                                                |
| Spring       | Spring Security CSRF on by default for sessions; risk: `csrf().disable()` left over from stateless-API setup                                   |
| Node/Express | nothing built-in — csurf/csrf-csrf middleware or an explicit Origin check must be wired                                                        |
| Vapor        | no built-in CSRF middleware — session-cookie apps need a form token (community middleware); cookie `SameSite` via `app.sessions.configuration` |
| .NET         | antiforgery built in — form tag helpers inject tokens, `AutoValidateAntiforgeryToken`; `[IgnoreAntiforgeryToken]` is the smell                 |
| Go           | gorilla/csrf or nosurf middleware; `SameSite` via `http.Cookie` — nothing is on by default                                                     |

## Example

Vulnerable shape — a mutation on GET, authenticated by a cookie:

```text
# router
GET /account/delete -> delete_account        # safe method: no CSRF middleware applies

handler delete_account(request):
    # auth: session cookie, sent automatically by the browser
    db.users.delete(request.session.user_id)
    # <img src="https://app.example/account/delete"> on any site triggers it
```

Fixed shape — unsafe method plus explicit origin proof:

```text
# router
POST /account/delete -> delete_account       # unsafe method: middleware covers it

handler delete_account(request):
    require csrf_token_valid(request)        # or validated Origin/Sec-Fetch-Site
    db.users.delete(request.session.user_id)
```

## Severity guidance

- **High** — missing protection on sensitive cookie-authenticated mutations
  (account changes, payments, permission grants); any state-changing GET.
- **Medium** — missing protection on low-impact mutations; important actions
  relying on SameSite alone.
- **Not a finding** — endpoints authenticated solely by Authorization
  headers; verify cookies truly play no part in the auth path before
  dismissing.
