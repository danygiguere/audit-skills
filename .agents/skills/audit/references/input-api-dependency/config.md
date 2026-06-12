# Configuration

## Invariant

Production configuration denies by default: debug and diagnostic surfaces
off, CORS limited to an explicit origin list, security headers present,
cookies marked Secure/HttpOnly/SameSite, and no default or example
credentials live. Anything permissive must be an explicit, justified
production decision — never an inherited dev convenience.

## Why it happens

Configuration is written once in development, where permissive settings
(debug pages, wildcard CORS, plain cookies) make iteration faster, and the
hardening step at deploy time is easy to forget because nothing breaks when
it is missing. Config is also split across files, env vars, middleware, and
infrastructure, so each layer assumes another one tightened things. Insecure
defaults shipped by frameworks and starter templates survive because they
work.

## Detection smells

- Debug/verbose-error mode controlled by an env flag that defaults to on,
  or hardcoded on, with no production override visible.
- CORS configured with a wildcard origin, or code that reflects the
  request's Origin header back — especially combined with allowing
  credentials, which turns "any site can read responses as the victim".
- No middleware or server layer setting security headers
  (content-security-policy, frame blocking, content-type-nosniff,
  strict-transport-security) anywhere in the stack.
- Session or auth cookies created without Secure, HttpOnly, or SameSite
  attributes; remember-me and CSRF cookies are the usual stragglers.
- Default accounts, example API keys, placeholder passwords, or seed-data
  admin users present in config or migrations with no removal step.
- Per-environment config files where a protection appears in the dev file
  but is absent (not just overridden) in the prod file — drift means prod
  silently falls back to framework defaults.
- Listening interfaces, admin panels, metrics, or debug endpoints exposed
  on all interfaces with no network or auth restriction.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where production config lives                                                                                                                             |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `config/environments/production.rb`; `force_ssl`; `consider_all_requests_local`                                                                           |
| Laravel      | `APP_DEBUG`/`APP_ENV` in `.env`; `config/cors.php`, `config/session.php`                                                                                  |
| Django       | `DEBUG`, `ALLOWED_HOSTS`, `SECURE_*`/`SESSION_COOKIE_*` settings; corsheaders config                                                                      |
| Spring       | `application-prod.yml` profiles; Spring Security headers and CORS configurers                                                                             |
| Node/Express | `NODE_ENV`; helmet for headers; `cors()` options; `cookie` flags on `res.cookie`                                                                          |
| Vapor        | `app.environment` gates debug behavior; `CORSMiddleware.Configuration` with explicit origins; cookie flags via `app.sessions.configuration.cookieFactory` |
| .NET         | `appsettings.{Environment}.json` + `ASPNETCORE_ENVIRONMENT`; CORS policy builder with explicit origins; dev pages gated by `IsDevelopment()`              |
| Go           | env-driven config (envconfig/viper); explicit CORS middleware; `http.Server` Read/Write timeouts are config too                                           |

## Example

Vulnerable shape:

```text
config:
    debug          = env("DEBUG", default = true)    # defaults open
    cors.origins   = "*"
    cors.allow_credentials = true                    # wildcard + credentials
    session_cookie = { }                             # no Secure/HttpOnly/SameSite
```

Fixed shape — closed unless explicitly opened, per environment:

```text
config:
    debug          = env("DEBUG", default = false)   # prod must opt in
    cors.origins   = env_list("ALLOWED_ORIGINS")     # explicit allowlist
    cors.allow_credentials = true                    # safe only with the list
    session_cookie = { secure: true, http_only: true, same_site: "lax" }
    headers        = { hsts, nosniff, frame_deny, csp }
```

## Severity guidance

- **Critical** — default/example credentials enabled in production, or
  debug consoles allowing code evaluation reachable in production.
- **High** — wildcard/reflected CORS with credentials; debug mode exposing
  stack traces, config values, or secrets; session cookies without
  Secure/HttpOnly on a credentialed app.
- **Medium** — missing security headers, missing SameSite, or env drift
  where a protection exists in dev but not prod without confirmed exposure.
- Findings in files that plausibly never reach production (local-only
  overrides) drop one level — but verify which file the deploy actually
  loads before assuming.
