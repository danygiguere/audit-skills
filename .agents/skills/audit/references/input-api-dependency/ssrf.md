# Server-Side Request Forgery (SSRF)

## Invariant

Whenever the server fetches a URL that any input can influence — webhook
targets, link previews, image fetchers, importers, callback URLs — the
destination is validated against an allowlist of hosts (or at minimum a
denylist of private/internal ranges enforced at connect time), and every
redirect hop is re-validated as a new destination. The server's network
position is a privilege; user input must not steer it.

## Does not apply when

- The URL is entirely server-defined (constants, config) with no
  input-influenced component — host, path, or query.

## Why it happens

Fetching a user-provided URL is the whole feature (webhooks, previews,
imports), so the dangerous flow is intentional; only the destination check
is missing. From inside the network, `localhost`, private ranges, and cloud
metadata endpoints are reachable even when nothing else is. Validation is
typically done once on the URL string, but the fetch resolves DNS later and
follows redirects — both of which can land somewhere the string check never
saw. URL parsers and the fetcher can disagree about what the host even is.

## Detection smells

- An HTTP client whose target URL (or any part — host, port, path) traces
  back to request input, a stored user record, or an external payload, with
  no destination allowlist before the fetch.
- Validation by string inspection only — prefix/substring/regex on the URL —
  with nothing rejecting private, loopback, link-local, or metadata IP
  ranges at resolution time (DNS can return a private address for a public
  name, including after the check: rebinding).
- The client follows redirects with no per-hop re-validation — an allowed
  public host can 302 to an internal address.
- Hostname compared with parser-confusable forms unhandled: credentials
  (`trusted.com@evil.com`), mixed-case/encoded characters, decimal or octal
  IP forms, IPv6 literals, trailing dots.
- Alternative schemes accepted (`file:`, `gopher:`, `ftp:`) because the code
  never pins the scheme to http/https.
- The fetch response (body, status, timing) returned to the caller —
  turning blind SSRF into a full read primitive against internal services.
- A function that constructs a URL from user input and returns it for a
  caller to fetch — follow the returned value to the actual request site
  before judging it safe.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where fetches and guards usually live                                                                                         |
|--------------|-------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Net::HTTP`/Faraday calls on user URLs; ssrf_filter-style resolved-IP guards                                                  |
| Laravel      | `Http::get($userUrl)`; guards as macros/middleware around the HTTP client                                                     |
| Django       | `requests.get(user_url)`; advocate-style validation or a guarded session wrapper                                              |
| Spring       | `RestTemplate`/`WebClient` with user URLs; checks in a `ClientHttpRequestInterceptor`                                         |
| Node/Express | `fetch`/axios/got on user URLs; resolved-address checks in a custom agent/lookup                                              |
| Vapor        | `req.client.get(URI(...))` — validate/allowlist the URI first; configure AsyncHTTPClient's redirect policy                    |
| .NET         | validate URI before `HttpClient`; `IHttpClientFactory` named clients with fixed base addresses; `AllowAutoRedirect` policy    |
| Go           | parse + allowlist before `http.Get`; custom `http.Client` with `CheckRedirect`; block private ranges via custom `DialContext` |

## Example

Vulnerable shape:

```text
handler preview(request):
    response = http.get(request.body.url)        # http://169.254.169.254/... works
    respond response.body                        # internal responses echoed back
```

Fixed shape — scheme pinned, host allowlisted, resolved IP checked, each
redirect re-validated:

```text
handler preview(request):
    url = parse_strict(request.body.url)
    if url.scheme not in {http, https}: respond 422
    if url.host not in ALLOWED_HOSTS: respond 422
    ip = resolve(url.host)
    if ip in PRIVATE_OR_METADATA_RANGES: respond 422
    response = http.get(url, follow_redirects = false,
                        connect_to = ip)          # fetch the IP we validated
    while response.is_redirect:
        url = parse_strict(response.location)
        re-run all checks above                   # each hop is a new destination
    respond sanitized(response)
```

## Open redirects

The inverse flow: the server (or a link) sends the **client** to an
attacker-controlled URL. Any redirect whose target comes from input — a
`return_to`/`next` parameter, a stored URL — must be allowlisted to known
paths/hosts or replaced by a server-side mapping of named destinations.
Smells: a redirect response whose location traces to a request parameter
with only prefix checks (`/`-prefixed strings like `//evil.com` and
`https:/evil.com` variants bypass them). Impact is phishing and, when the
redirect sits inside an auth flow, token or credential capture.

## Severity guidance

- **Critical** — SSRF with the response readable, reaching cloud metadata
  credentials or internal admin services.
- **High** — blind SSRF (no response echo) that can still hit internal
  services, or readable SSRF restricted to a partial surface.
- **Medium** — destination steering limited to public hosts (port scanning,
  request laundering), or redirect-hop validation missing atop an otherwise
  sound allowlist.
- Open redirects are **Medium** alone; **High** when embedded in an
  authentication or OAuth flow where the redirect carries tokens.
