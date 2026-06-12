# Cryptography & Data Protection

## Invariant

Passwords are hashed with an adaptive, salted algorithm (bcrypt, scrypt,
argon2 class). Security tokens come from a cryptographically secure random
source. Secrets are compared in constant time. Encryption uses an
established library in an authenticated mode, with keys loaded from
configuration, never from source. Data whose compromise is itself a breach
is encrypted at rest. Nothing is hand-rolled from primitives.

## Why it happens

The general-purpose primitives are the discoverable ones — `md5`, `sha1`,
`random()`, `==` — and they appear to work, so nothing forces the secure
choice. Fast hashes feel fine for passwords because the threat (offline
cracking of a dumped table) never shows up in development. ECB is still the
default mode in several libraries. Keys get hardcoded to make tests pass and
then never move; comparison timing leaks are invisible without measuring.

## Detection smells

- Password storage uses a fast hash (MD5/SHA family, salted or not),
  reversible encryption, or plaintext.
- Tokens, OTPs, or session/reset identifiers built from non-cryptographic
  randomness, timestamps, user IDs, or hashes of predictable input.
- Secret, token, or signature comparison via ordinary string equality —
  early-exit comparison is a timing oracle for MACs and tokens.
- Encryption with ECB mode, a static or zero IV, or no authentication (raw
  CBC/CTR with no MAC) — or any custom scheme stitching primitives together.
- Keys, salts, peppers, or IVs as literals in source or committed config.
- Sensitive fields (government IDs, payment data, health records,
  third-party credentials) stored plaintext where the data class warrants
  encryption at rest.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Standard tools                                                                                                                                  |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `has_secure_password` (bcrypt); `SecureRandom`; `ActiveSupport::SecurityUtils.secure_compare`; `ActiveRecord::Encryption`                       |
| Laravel      | `Hash::make` (bcrypt/argon2); `Str::random`/`random_bytes`; `hash_equals`; `Crypt` and `encrypted` casts                                        |
| Django       | `PASSWORD_HASHERS` (argon2/pbkdf2); `secrets` module; `constant_time_compare`; `cryptography` Fernet                                            |
| Spring       | `BCryptPasswordEncoder`/`Argon2PasswordEncoder`; `SecureRandom`; `MessageDigest.isEqual`; JCA AES-GCM                                           |
| Node/Express | `bcrypt`/`argon2` packages; `crypto.randomBytes`; `crypto.timingSafeEqual`; `createCipheriv` with GCM                                           |
| Vapor        | `app.password`/`Bcrypt` for passwords; swift-crypto (`AES.GCM`, `SHA256`, `HMAC`); `[UInt8].random(count:)` (CSPRNG) for tokens                 |
| .NET         | Identity `PasswordHasher` (PBKDF2); `RandomNumberGenerator` for tokens; `CryptographicOperations.FixedTimeEquals`; Data Protection API for keys |
| Go           | x/crypto bcrypt/argon2; `crypto/rand` — never `math/rand` for tokens; `subtle.ConstantTimeCompare`                                              |

## Example

Vulnerable shape:

```text
create_reset_token(user):
    token = md5(user.id + now())            # predictable; brute-forceable
    db.save(user.id, token)                 # stored plaintext — a DB read = takeover

verify_reset_token(user, supplied):
    return supplied == db.token_for(user)   # early-exit comparison: timing leak
```

Fixed shape:

```text
create_reset_token(user):
    token = csprng_bytes(32).hex()          # unpredictable
    db.save(user.id, sha256(token), expires = now() + 1h)   # store digest only
    return token                            # plaintext exists only in the email

verify_reset_token(user, supplied):
    return constant_time_equal(sha256(supplied), db.digest_for(user))
```

## Severity guidance

- **Critical** — passwords plaintext, reversible, or fast-hashed; hardcoded
  production keys guarding sensitive data.
- **High** — predictable security tokens (session, reset, API);
  unauthenticated or ECB-mode encryption of sensitive data; homemade
  constructions on authentication paths.
- **Medium** — non-constant-time comparison of secrets (raise when remotely
  measurable, e.g. webhook signatures); missing at-rest encryption where the
  data class warrants it.
- Weak primitives on non-secret data (checksums, cache keys, ETags) are not
  findings — confirm what the value protects before reporting.
