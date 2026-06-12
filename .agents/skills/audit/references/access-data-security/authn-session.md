# Authentication & Session Management

## Invariant

Sessions are replaced on every privilege change — a fresh session identifier
is issued at login, and the server-side session is destroyed at logout, not
just the cookie. Credential flows (login, signup, password reset) respond
identically in content and time whether or not the account exists. Reset and
remember-me tokens are unpredictable, single-use, expiring, and stored
hashed; failed attempts are rate-limited.

## Why it happens

Session fixation survives because "log the user in" mutates the existing
session instead of replacing it, and frameworks differ on whether
regeneration is automatic. Enumeration leaks come from helpful error
messages and from short-circuiting — returning early when no user is found
skips the slow password hash, so timing reveals existence. Reset tokens stay
plaintext and reusable because the happy path never exercises a second use,
and lockout is a feature nobody schedules until after the credential-stuffing
incident.

## Detection smells

- The login success path writes the user ID into the current session without
  issuing a new session identifier first.
- Logout clears the cookie client-side but never invalidates the session
  record server-side — a captured session token still works after logout.
- Responses differ by account existence: "no such user" vs "wrong password",
  signup's "email already taken", reset's "no account with that email".
- Password verification is skipped entirely when the user lookup fails — the
  fast path is a timing oracle for account existence.
- No lockout, counter, or rate limit on failed login or reset attempts
  (needed both per-account and per-source).
- Reset tokens that never expire, survive use or a completed password
  change, sit in the database in plaintext, or derive from predictable input
  (timestamp, user ID, sequential value).
- Remember-me cookies containing the user ID or a reversible value instead
  of a random token whose hash is stored server-side.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the controls usually live                                                                                                                                       |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `reset_session` before sign-in; Devise `:lockable`/`:recoverable` (hashed, expiring tokens)                                                                           |
| Laravel      | `$request->session()->regenerate()` on login, `invalidate()` on logout; `throttle` middleware; Password broker                                                        |
| Django       | `auth.login()` rotates the session key; `PasswordResetTokenGenerator`; django-axes for lockout                                                                        |
| Spring       | Spring Security session-fixation protection (migrate/new session); logout handlers; custom token services                                                             |
| Node/Express | `req.session.regenerate()` / `req.session.destroy()` are manual; `crypto.randomBytes` tokens; express-rate-limit                                                      |
| Vapor        | `SessionsMiddleware` + `ModelSessionAuthenticatable`; `req.auth.login`/`logout` + `req.session.destroy()`; reset tokens are hand-rolled — check expiry and single-use |
| .NET         | ASP.NET Core Identity (lockout, single-use reset tokens built in); `SignInAsync`/`SignOutAsync`; cookie auth options for expiry                                       |
| Go           | gorilla/sessions or SCS — `RenewToken` on login; server-side destroy on logout; bcrypt; uniform login/reset errors against enumeration                                |

## Example

Vulnerable shape:

```text
handler login(request):
    user = db.users.find_by_email(request.body.email)
    if user is null:
        respond 401 "no account for that email"      # enumeration by message + timing
    if not verify(user.password_hash, request.body.password):
        respond 401 "wrong password"                 # confirms the account exists
    session.user_id = user.id                        # fixation: pre-login session ID kept
```

Fixed shape — uniform failure, equalized work, fresh session:

```text
handler login(request):
    user = db.users.find_by_email(request.body.email)
    hash = user ? user.password_hash : DUMMY_HASH    # always pay the hash cost
    ok   = verify(hash, request.body.password) and user is not null
    if not ok: respond 401 "invalid credentials"     # one message for every failure
    session.regenerate()                             # new ID before privilege change
    session.user_id = user.id
```

## Severity guidance

- **High** — session not regenerated on login (fixation); logout that leaves
  the server-side session valid; reset tokens that are predictable,
  reusable, or non-expiring.
- **Medium** — account enumeration via message or timing differences;
  missing lockout/rate limiting on credential endpoints; remember-me tokens
  stored unhashed.
- Enumeration **plus** missing rate limiting together enable credential
  stuffing — report the pair as High even if each alone is Medium.
