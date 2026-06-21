# Insecure Deserialization

## Invariant

Bytes that arrive from outside the trust boundary — a request body, header,
cookie, queue message, cache entry, uploaded file, or another service — are
never fed to a deserializer that can instantiate arbitrary types or invoke
code while reconstructing the object graph. Untrusted input is parsed only
with a data-only format (JSON, a fixed protobuf/Avro schema) into a known
target type, or, where an object format is unavoidable, restricted by a
server-defined type allowlist and authenticated with a signature the receiver
verifies before deserializing.

## Does not apply when

- The serialized bytes never cross a trust boundary — produced and consumed
  by the same process, or exchanged only between services inside the trust
  boundary over an authenticated channel, with no path for an attacker to
  substitute the payload.

## Why it happens

Native serializers are the convenient default for caching, sessions, queues,
and inter-service calls because they round-trip a live object in one call —
no schema, no mapping code. The danger is invisible: the same `loads` /
`readObject` / `unserialize` that revives a value will, on a crafted payload,
construct attacker-chosen types and run their magic methods (constructors,
`__reduce__`, `readObject`, `__wakeup__`, type converters) — a gadget chain
that reaches code execution without any obvious `eval`. It looks like parsing,
so reviewers wave it through; and the source is often trusted by habit
("it's our own cache / our own queue"), even when an attacker can write to
that cache key or enqueue that message.

## Detection smells

- Untrusted bytes handed to a native object deserializer: `pickle.loads`,
  Java `ObjectInputStream.readObject`, PHP `unserialize`, Ruby `Marshal.load`,
  .NET `BinaryFormatter`/`NetDataContractSerializer`/`SoapFormatter`, Python
  `yaml.load` without `SafeLoader`.
- A session, cookie, cache value, or queue message stored as a serialized
  object graph rather than a data-only encoding — anyone who can write the
  store controls the gadget input.
- A polymorphic JSON/XML mapper configured to embed and honor concrete type
  names from the payload (Jackson default/polymorphic typing, `Newtonsoft`
  `TypeNameHandling.All`, `XmlSerializer`/`DataContractSerializer` over an
  open type hierarchy).
- A type allowlist that is absent, or present but permissive (matches a
  package prefix, or includes types with dangerous side effects in their
  constructors/finalizers).
- "Trusted source" reasoning applied to a channel an attacker can influence —
  a cache key derived from user input, a queue any tenant can publish to.
- Signature/MAC verification that happens *after* deserialization, or not at
  all, on a payload that carries an object graph.
- XML parsing left at default settings (external entities and DTDs enabled),
  turning deserialization into XXE — file read and SSRF.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Safe primitive vs the trap                                                                                                       |
|--------------|----------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `JSON.parse` / typed `ActiveModel` vs `Marshal.load`; `YAML.safe_load` vs `YAML.load`; signed/encrypted cookies, not marshalled  |
| Laravel      | `json_decode` to a DTO vs PHP `unserialize`; encrypted+signed session payloads vs raw serialized blobs                           |
| Django       | DRF serializers / `json.loads` vs `pickle`; `SESSION_SERIALIZER = JSONSerializer`; `yaml.safe_load` only                         |
| Spring       | Jackson with default typing **off** + `@JsonTypeInfo` allowlist vs Java `ObjectInputStream`; avoid serialization-based sessions   |
| Node/Express | `JSON.parse` into a validated schema vs `node-serialize`/`eval`-based revivers; never `vm`/`Function` on payloads                 |
| Vapor        | `Codable` from JSON into a concrete type vs `NSKeyedUnarchiver` with `requiringSecureCoding: false`                               |
| .NET         | `System.Text.Json` to a target type vs `BinaryFormatter`/`TypeNameHandling.All`; set `TypeNameHandling.None`                      |
| Go           | `encoding/json` into a struct vs `encoding/gob` over untrusted bytes; bound and validate after `Unmarshal`                        |

## Example

Vulnerable shape — a session cookie carrying a native object graph, revived
before any check:

```text
handler load_session(request):
    blob = base64_decode(request.cookie["session"])
    user = native_deserialize(blob)        # gadget chain runs here, pre-auth
    return user
```

Fixed shape — data-only format into a known type, signature verified first:

```text
handler load_session(request):
    raw = request.cookie["session"]
    if not hmac_verify(raw.body, raw.sig, server_key):   # verify before parse
        respond 401
    data = json_parse(raw.body)            # data only — no types from payload
    return Session(user_id = require_int(data["uid"]),   # mapped to known shape
                   role    = require_enum(data["role"], ROLES))
```

## Severity guidance

- **Critical** — a native/polymorphic deserializer reachable with
  attacker-controlled bytes on an unauthenticated path, where a known or
  plausible gadget chain yields remote code execution.
- **High** — the same sink behind authentication or requiring a prior write
  the attacker can perform (a cache key or queue they can reach), or XXE
  giving arbitrary file read / SSRF.
- **Medium** — polymorphic typing enabled with no demonstrated gadget today,
  or a deserializer reachable only via a narrow, privileged channel — latent
  but exploitable as dependencies change.
- **Low** — data-only parsing with no type instantiation risk, but missing
  the post-parse bounds/shape validation that would harden it; flag as a
  hardening note.
