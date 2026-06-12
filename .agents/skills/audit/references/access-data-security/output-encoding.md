# Output Encoding

## Invariant

Every user-controlled value written into output is encoded for the exact
context it lands in — HTML body, HTML attribute, JavaScript, URL, CSS, HTTP
header, or email — at the moment of rendering. Encoding for one context does
not cover another. A Content-Security-Policy limits the blast radius; it is
defense-in-depth, never a substitute for encoding.

## Does not apply when

- The output is machine-consumed JSON served with the correct content type
  (`application/json`, ideally with `nosniff`) and never interpolated into
  HTML server-side — the consuming client then owns its own render context.

## Why it happens

Template engines auto-escape for the HTML-body context only, so developers
stop thinking about context at all. Raw-output helpers exist for legitimate
cases and spread by copy-paste. Building markup, scripts, or emails by
string concatenation bypasses escaping entirely. Values that look safe at
write time (usernames, filenames) become vectors when an upstream validation
loosens — encoding must not depend on input cleanliness.

## Detection smells

- Template sinks that explicitly disable escaping (raw/unsafe/trusted-HTML
  markers) fed values traceable to request input or user-authored fields.
- HTML, JavaScript, or email bodies assembled by string concatenation or
  interpolation instead of a context-aware template.
- User data placed in a context its escaping does not cover: inside a script
  block, an event-handler or `href`/`src` attribute, an unquoted attribute,
  or a style block, while only HTML-entity encoded.
- User input flowing into a redirect target or response header value without
  validation (open redirect, header injection).
- Client-side code assigning request or user data to innerHTML-class sinks
  or feeding it to an HTML parser.
- URLs built by concatenating user input rather than per-component encoding.
- Reliance on a sanitize-on-input pass instead of encode-on-output — input
  filtering cannot know the eventual context and decays as code moves.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Escaping defaults and raw sinks                                                                                                |
|--------------|--------------------------------------------------------------------------------------------------------------------------------|
| Rails        | ERB escapes by default; `raw`, `.html_safe`, `<%==` bypass; `sanitize` for rich text                                           |
| Laravel      | Blade `{{ }}` escapes; `{!! !!}` bypasses; `e()` helper                                                                        |
| Django       | templates autoescape; `                                                                                                        |safe`, `mark_safe`, `{% autoescape off %}` bypass    |
| Spring       | Thymeleaf `th:text` escapes, `th:utext` bypasses; JSP `${}` is raw, `<c:out>` escapes                                          |
| Node/Express | engine-dependent — EJS `<%= %>` escapes, `<%- %>` raw; Handlebars `{{ }}` vs `{{{ }}}`; concatenated `res.send` has none       |
| Vapor        | Leaf escapes `#(...)` by default; `#unsafeHTML(...)` is the raw sink; JSON via `Content` is safe unless later rendered as HTML |
| .NET         | Razor encodes `@Model.Name` by default; `Html.Raw(...)` is the raw sink; tag helpers are safe                                  |
| Go           | `html/template` auto-escapes per context; using `text/template` for HTML is the smell; `template.HTML(...)` is the raw sink    |

## Example

Vulnerable shape — one value, two unprotected contexts:

```text
handler search(request):
    q = request.query.q
    respond html("<h1>Results for " + q + "</h1>"             # HTML-body injection
        + "<a href='/search?q=" + q + "&page=2'>next</a>")    # attribute + URL contexts
```

Fixed shape — the renderer encodes per context:

```text
handler search(request):
    q = request.query.q
    respond template("results",
        heading  = q,                                    # entity-encoded in HTML body
        next_url = url("/search", query = {q: q, page: 2}))  # URL-component encoded,
                                                              # then attribute-encoded
```

## Severity guidance

- **High** — stored XSS (user-authored content rendered unescaped to other
  users); reflected XSS on authenticated pages; header injection enabling
  response splitting or cookie setting.
- **Medium** — reflected XSS requiring a crafted link on low-value pages;
  open redirects; HTML injection without script execution.
- User input rendered unescaped in admin-facing views is privilege
  escalation — rate it High regardless of where the input entered.
- A strong CSP lowers exploitability, not the finding — the missing encoding
  is still the bug.
