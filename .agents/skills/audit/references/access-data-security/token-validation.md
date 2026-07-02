# Token & Webhook Validation

## Invariant

Every stateless credential presented to the application — JWT, API key,
signed URL, webhook signature — is cryptographically verified before any
claim inside it is trusted. Verification pins the expected algorithm and
key, and validates the claims that scope the token: expiry (`exp`/`nbf`),
audience (`aud`), issuer (`iss`). Webhook payloads are authenticated with
the provider's signature computed over the **raw** request body, inside a
bounded timestamp window. Decoding a token is parsing, not authentication —
a decoded-but-unverified claim is attacker input.

## Does not apply when

- The token is an opaque session identifier looked up in server-side state
  — nothing in the value is trusted, only the lookup (that flow belongs to
  `authn-session.md`).
- Verification demonstrably happens earlier in the chain (gateway,
  middleware, framework authenticator) and the handler receives the already
  verified principal — cite where.

## Why it happens

JWT libraries ship `decode()` and `verify()` as sibling calls, and
`decode()` returns perfectly readable claims — the missing signature check
is invisible in every happy-path test. The token's `alg` header is
attacker-controlled but looks like configuration, so verifiers that honor
it accept `none` or let an RSA public key be replayed as an HMAC secret.
Webhook handlers work end-to-end in development without the signature
check, so it ships; the replay window never comes up. Multi-service setups
share an issuer, and nobody validates `aud`, so a token minted for one
service opens another.

## Detection smells

- Claims read before or without verification: `jwt.decode(...)` (no key,
  `verify=False`, `{ complete: true }`) feeding authorization decisions;
  "parse the token to get the user id" helpers.
- Algorithm not pinned by the **verifier**: no `algorithms=[...]` allowlist,
  `none` accepted, or one code path verifying both HS256 and RS256 with the
  same key material — the RSA public key becomes a known HMAC secret
  (algorithm confusion).
- Key selection driven by attacker-controlled headers: `kid` used to build
  a file path, SQL lookup, or URL; embedded `jwk`/`jku`/`x5u` honored — the
  token ships its own trust anchor.
- Missing claim validation: no `exp` check (or clock skew tolerance of
  hours), `aud`/`iss` ignored where more than one service or tenant shares
  the signing authority, token type not checked (refresh token accepted as
  access token, reset token as session).
- JWKS fetched over plain HTTP, cached forever (revoked keys live on) or
  not at all (fetch per request — availability), or matched by `kid` without
  restricting to the expected issuer's key set.
- Webhook handler acts on the parsed body without checking the provider's
  signature header, compares the signature with `==` instead of a
  constant-time function, computes the HMAC over the re-serialized JSON
  instead of raw bytes (byte-for-byte mismatch → devs then disable the
  check), or verifies the signature but ignores the timestamp — a captured
  request replays forever.
- Signed URLs or unsubscribe/confirm links where the signature does not
  cover every security-relevant parameter, so unsigned parameters can be
  swapped.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Verified path vs the trap                                                                                                       |
|--------------|-----------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `JWT.decode(t, key, true, algorithm:, verify_aud:, aud:)` — the `true` is the verify flag; Stripe `Webhook.construct_event(request.raw_post, sig, secret)` |
| Laravel      | firebase/php-jwt `JWT::decode($t, new Key($pem, 'RS256'))` — Key pins the alg; `hash_equals()` for HMACs; Cashier's webhook signature middleware |
| Django       | PyJWT `jwt.decode(t, key, algorithms=["RS256"], audience=..., issuer=...)` vs `verify=False`/no `algorithms`; `hmac.compare_digest` on raw `request.body` |
| Spring       | `JwtDecoder` (Nimbus) with `JwtValidators` for issuer/audience/timestamp; resource-server autoconfig verifies — hand-rolled `SignedJWT.parse` does not |
| Node/Express | `jsonwebtoken.verify(t, key, { algorithms, audience, issuer })` — `jwt.decode()` checks **nothing**; `crypto.timingSafeEqual`; raw-body middleware for webhook routes |
| Vapor        | JWTKit `req.jwt.verify(as: Payload.self)` with configured signers vs decoding the base64 segments by hand                          |
| .NET         | `TokenValidationParameters` — `ValidateIssuer/Audience/Lifetime/IssuerSigningKey` all true; `RequireSignedTokens`; JwtBearer middleware |
| Go           | golang-jwt `jwt.NewParser(jwt.WithValidMethods([...]))` + keyfunc rejecting unexpected `token.Method`; `hmac.Equal` over the raw body |

## Example

Vulnerable shape — decoded claims trusted, webhook body trusted:

```text
handler api_request(request):
    claims = jwt_decode(request.header["Authorization"])   # no signature check;
    current_user = load_user(claims["sub"])                 # alg/aud/exp never seen

handler payment_webhook(request):
    event = json_parse(request.body)                        # unauthenticated input
    if event["type"] == "paid": mark_order_paid(event["order_id"])
```

Fixed shape — verify first, pin the algorithm, bound the replay window:

```text
handler api_request(request):
    claims = jwt_verify(request.header["Authorization"],
                        key = ISSUER_KEYS,                  # server-chosen, not kid-built
                        algorithms = ["RS256"],             # pinned allowlist, never "none"
                        audience = "orders-api",
                        issuer = "https://auth.example.com")  # exp/nbf checked by verify
    current_user = load_user(claims["sub"])

handler payment_webhook(request):
    sig, ts = parse_sig_header(request.header["Signature"])
    expected = hmac_sha256(WEBHOOK_SECRET, ts + "." + request.raw_body)
    if not constant_time_eq(sig, expected): respond 401     # raw bytes, not re-serialized
    if abs(now() - ts) > 5.minutes: respond 401             # replay window
    event = json_parse(request.raw_body)
    if event["type"] == "paid": mark_order_paid(event["order_id"])
```

## Severity guidance

- **Critical** — unverified decode, `alg: none` acceptance, or algorithm
  confusion on an authentication path: anyone who can mint a token
  impersonates any principal. A state-changing webhook (payments, account
  status) accepted without signature verification.
- **High** — signature verified but `aud`/`iss` unvalidated where multiple
  services or tenants share an issuer (cross-service token replay); missing
  `exp` enforcement; a correctly signed webhook accepted without a
  timestamp window (indefinite replay); key selection influenced by
  attacker-controlled `kid`/`jku`.
- **Medium** — non-constant-time signature comparison (needs a network
  timing oracle); token type confusion between same-issuer tokens of
  similar privilege; signed URLs whose signature omits a low-impact
  parameter.
- **Low** — generous but bounded clock-skew tolerance; JWKS caching
  weaknesses with rotation still possible.
