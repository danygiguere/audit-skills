# Parser Differentials

## Invariant

A validator, parser, or matcher that gates an input must interpret that
input **exactly as the downstream consumer does**. If there exists an input
the gate accepts but the consumer understands differently — a different
host, path, type, or command — the gate is decoration. The finding is the
differential: name both sides.

## Does not apply when

- The gate validates the *parsed object* and the consumer uses **that same
  object** — parse once, validate the result, pass the result on. The
  differential requires two interpretations of the raw input.

## Why it happens

Validation and consumption are written at different times against different
mental models of the input. Regexes default to partial matching; URL
grammars are genuinely ambiguous (userinfo, encoding, backslashes); two
libraries "parsing URLs" rarely agree on every edge. Developers test the
inputs they expect — attackers send the ones parsers disagree on. And the
most common shape guarantees the bug: validate the raw string, then pass
the raw string downstream to be parsed *again* by something else.

## Detection smells

- An unanchored or partial-match regex used as a gate — missing start/end
  anchors, or anchors that stop at a newline; `evil.com\ngood.com` passes.
- An allowlist checked with substring/startswith/endswith:
  `paypal.com` is matched by `evilpaypal.com` and `paypal.com.evil.net`.
- A URL checked with one parser and fetched with another — userinfo (`@`),
  backslashes, double-encoding, and mixed-case schemes are where they
  disagree.
- Normalization on one side only: the validator lowercases, decodes, or
  unicode-normalizes and the consumer doesn't (or vice versa);
  `%2e%2e` vs `..`.
- Content-type or extension checked at the gate while the consumer sniffs
  the body (polyglot files).
- A strict validator in front of a lenient decoder: the gate checks the
  JSON/XML shape, the consumer's decoder also accepts trailing data,
  duplicate keys, or comments.
- Validate-then-reparse: the gate parses the raw input, then passes the
  **raw input** on, and the consumer parses it again.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where the discipline usually lives                                              |
|--------------|----------------------------------------------------------------------------------|
| Rails        | `=~`/`match` are partial — anchor with `\A...\z` (not `^$`, which stop at newlines); `start_with?` allowlists; `URI.parse` vs Addressable disagreements |
| Laravel      | `preg_match` without anchors; `$` matching before a trailing newline; `Str::startsWith` allowlists; `FILTER_VALIDATE_URL` vs `parse_url` disagreements |
| Django       | `re.match` anchors the start only — use `re.fullmatch`; `urlparse` vs what `requests` actually fetches; `startswith` allowlists |
| Spring       | `Matcher.find()` is unanchored (`matches()` is not); `java.net.URI` vs Apache/commons parsers; matcher-vs-dispatcher mismatches in security rules |
| Node/Express | legacy `url.parse()` vs WHATWG `new URL()` — the classic SSRF differential; regex without `^$`; `.startsWith` allowlists; decode-after-normalize ordering |
| Vapor        | `hasPrefix` allowlists; Foundation `URL` vs other URI parsers; `NSRegularExpression` partial matches |
| .NET         | `Regex.IsMatch` without `^$`; `Uri` quirks (trailing dots, scheme case); `StartsWith` without ordinal comparison |
| Go           | `regexp` is unanchored by default — anchor explicitly; `net/url` leniency (userinfo, backslashes historically); `strings.HasPrefix` allowlists |

## Example

Vulnerable shape — unanchored gate, and the raw string is re-parsed by the
fetcher:

```text
handler fetch_preview(request):
    url = request.body.url
    if regex_match("https://([a-z]+\.)?example\.com", url):  # unanchored
        return http.get(url)                                 # re-parses raw
# passes the gate: "https://example.com.evil.net/"   (no end anchor)
# passes the gate: "https://x@evil.net\\@example.com" when the fetcher's
#                  parser reads a different host than the regex saw
```

Fixed shape — one parser, exact comparison, and the consumer receives the
parsed object:

```text
handler fetch_preview(request):
    parsed = url.parse_strict(request.body.url)
    if parsed is null:                respond 422
    if parsed.scheme != "https":      respond 422
    if parsed.host not in ALLOWED:    respond 422   # exact match, parsed side
    return http.get(parsed)                         # the SAME object is used
```

## Severity guidance

- **Critical** — the differential bypasses an allowlist protecting an
  exec/loader sink or the internal network (see `ssrf.md`, `injection.md`).
- **High** — it bypasses a security gate: redirect validation, path jail,
  authorization matcher, file-type restriction.
- **Medium** — it bypasses input validation feeding business logic (wrong
  type, range, or format reaching the consumer).
- **Low** — gate and consumer disagree but the consumer's own strictness
  happens to cover it today; fragile, not exploitable as-is.
