# File handling

## Invariant

No filesystem path is ever derived from raw input: client-supplied names
are replaced with server-generated identifiers, or resolved and verified to
stay inside the intended root. Uploads are constrained by content-verified
type, size limits, and a storage location that is outside the web root and
never executable.

## Why it happens

Joining a base directory with a request parameter looks safe because the
base is fixed — but `..` segments, absolute paths, and encoded separators
let the joined result escape it. The client's filename and content-type
arrive pre-filled in the upload object, so using them feels like reading
data, not trusting an attacker. Extraction libraries faithfully honor entry
paths inside archives. Size limits and storage placement are deployment
concerns nobody owns in application code.

## Detection smells

- A path built by joining a base directory with a request parameter,
  filename, or header, used for read, write, or delete without resolving it
  and verifying the result is still under the base.
- An uploaded file stored under its original client-supplied name — even
  "sanitized" names that strip only `../` miss absolute paths, drive
  letters, null bytes, and encoded separators.
- Type enforcement based on the client-sent content-type header or the
  filename extension, with no inspection of actual content (magic bytes) —
  both are attacker-chosen fields.
- No size limit on the upload path, or limits only at a proxy the code does
  not control; unbounded reads of the upload into memory.
- Uploads written inside the web/public root, or to a location served with
  script-execution enabled — a stored file becomes a deployable payload.
- Archive extraction that writes entries using their embedded paths without
  validating each resolved destination stays inside the target directory
  (zip-slip); symlinked entries pointing outside count too.
- Download/serve endpoints that take a filename or relative path parameter
  and stream the file back — read-side traversal leaks source and secrets.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Safe-handling idiom                                                                                                                       |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | Active Storage (generated keys, off-root storage); `send_file` from fixed dirs                                                            |
| Laravel      | `Storage` disks with `store()`/`hashName()`; never `move()` with the client name                                                          |
| Django       | `FileField` `upload_to` + storage backend; `get_valid_filename`; MEDIA outside static                                                     |
| Spring       | `MultipartFile` size limits; `Path.resolve(...).normalize()` + `startsWith(base)`                                                         |
| Node/Express | multer with generated filenames and limits; `path.resolve` + prefix check on base                                                         |
| Vapor        | `req.fileio` for reads/writes — never path-join request input; `FileMiddleware` serves only `Public/`; body caps via `.collect(maxSize:)` |
| .NET         | `IFormFile` + `[RequestSizeLimit]`; `Path.GetFileName` to strip client paths; serve via `PhysicalFile` from storage outside wwwroot       |
| Go           | `filepath.Base`/`Clean` + root containment check; `http.MaxBytesReader`; `http.ServeFile` with user-built paths is the smell              |

## Example

Vulnerable shape:

```text
handler download(request):
    path = "/srv/app/uploads/" + request.query.name   # ?name=../../etc/passwd
    respond file(path)

handler upload(request):
    if request.file.content_type != "image/png": respond 415   # client-chosen
    write("/srv/app/public/" + request.file.original_name, ...) # web root, own name
```

Fixed shape — server-generated names, resolved-path check, content-based
type, bounded size, off-root storage:

```text
handler download(request):
    record = db.files.find(request.params.id)         # lookup, not a path
    full = resolve(UPLOAD_ROOT + "/" + record.stored_name)
    if not full.starts_with(UPLOAD_ROOT): respond 404
    respond file(full, as = record.display_name)

handler upload(request):
    if request.file.size > MAX_SIZE: respond 413
    if sniff_magic_bytes(request.file) not in ALLOWED_TYPES: respond 415
    stored = generate_id() + canonical_extension       # client name only as metadata
    write(UPLOAD_ROOT + "/" + stored, request.file)    # outside web root, no exec
```

## Severity guidance

- **Critical** — write-side traversal or zip-slip (arbitrary file write),
  or uploads stored where the server executes them (remote code execution).
- **High** — read-side traversal reaching files outside the intended root
  (source, config, secrets).
- **Medium** — type checks relying only on extension/client content-type,
  or missing size limits enabling disk/memory exhaustion.
- **Low** — original filenames stored but only ever used as display
  metadata, with generated names on disk.
- Severity tracks what the escaped path can reach: a traversal jailed
  inside an empty directory tree is lower than one on a shared host.
