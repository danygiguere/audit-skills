# Secrets

## Invariant

Credentials — API keys, database passwords, signing keys, tokens — live
only in environment variables or a secret manager, scoped to the least
privilege the consumer needs, and replaceable without a code change. They
never appear in source, version-control history, logs, error reports, or
code delivered to clients.

## Why it happens

Hardcoding a key is the fastest way to make an integration work, and the
intention to "move it to env later" rarely survives the merge. Once
committed, a secret lives in VCS history even after the line is deleted, and
nobody treats deletion as the rotation event it is. Logging and error
reporters capture whole request/config objects by default, sweeping secrets
along. Broad keys persist because narrowing scopes requires understanding
every consumer.

## Detection smells

- String literals shaped like credentials (long high-entropy tokens,
  `sk_`/`AKIA`-style prefixes, connection strings with embedded passwords)
  assigned in source or test fixtures rather than read from the environment.
- `.env` or equivalent files tracked in version control, or absent from
  ignore rules — and even when now ignored, history may still contain them
  (deleting the file does not revoke the key).
- Log statements or error-reporter payloads that serialize whole config,
  request, or header objects on paths where credentials transit
  (Authorization headers, webhook signing secrets, DB URLs).
- One credential used by many components or with full-account scope, where
  any single consumer needs only a fraction of its permissions.
- A secret referenced by literal value in multiple places, with no single
  injection point — rotation would require a coordinated code change, so in
  practice it never happens.
- Secrets compiled or bundled into client-delivered code — mobile binaries,
  browser bundles, public build-time variables — where "private" key types
  are extractable by anyone.
- A new credential or token type introduced without wiring it into the
  existing rotation, revocation, and log-redaction lists — it silently
  misses every protection keyed on the old set.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Idiomatic secret source                                                                                                         |
|--------------|---------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Rails.application.credentials` (encrypted) or `ENV.fetch`; `filter_parameters`                                                 |
| Laravel      | `env()` consumed only inside `config/*`; `.env` git-ignored; `config:cache` caveats                                             |
| Django       | `os.environ` / django-environ in `settings.py`; never literals in settings                                                      |
| Spring       | externalized config, Vault/Cloud Config; `${...}` placeholders, not literals                                                    |
| Node/Express | `process.env` via dotenv or platform secrets; beware front-end build-var prefixes                                               |
| Vapor        | `Environment.get("API_KEY")`; `.env` loaded by Vapor's dotenv support — never committed                                         |
| .NET         | user-secrets in dev; `IConfiguration` from env vars / Key Vault in prod; credentials in committed appsettings.json is the smell |
| Go           | env vars / secret managers; beware logging whole config structs (`%+v`)                                                         |

## Example

Vulnerable shape:

```text
payment_client = PaymentApi(key = "sk_live_9f3a...")     # in source + history
logger.info("payment request", request.headers)          # Authorization logged
frontend_bundle.config = { PAYMENT_SECRET: key }         # shipped to clients
```

Fixed shape — one injection point, scoped key, redacted telemetry:

```text
payment_client = PaymentApi(key = env.require("PAYMENT_KEY"))  # charge-only scope
logger.info("payment request", redact(request.headers,
            ["authorization", "cookie", "x-api-key"]))
# clients receive only a publishable key or short-lived server-minted token
```

## Severity guidance

- **Critical** — a live production credential present in source, VCS
  history, client bundles, or logs; treat as compromised and rotate, not
  merely remove.
- **High** — secrets flowing into logs or error reporters in production, or
  a single all-permissions key shared across services.
- **Medium** — hardcoded credentials for non-production systems, missing
  redaction on paths where secrets could plausibly transit, or no viable
  rotation path.
- A revoked or clearly fake/test placeholder value drops to low — but
  verify revocation; "looks old" is not revoked.
