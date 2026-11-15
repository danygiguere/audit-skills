# Dependencies & Supply Chain

## Invariant

Every piece of third-party code that reaches the build or the runtime —
packages, transitive packages, base images, CI actions, downloaded scripts
and binaries — is resolved to an exact, immutable version recorded in the
repository, fetched from the registry it was meant to come from, and
verified against a recorded hash. The same inputs always produce the same
dependency tree; nothing an outside party can republish is trusted by name
alone, and versions with known vulnerabilities on a reachable path are not
shipped.

## Does not apply when

- The package is a published **library**: its manifest should declare
  compatible ranges, not exact pins — consumers do the locking. (Its own
  CI and development installs still use a lockfile.)
- Dependencies are vendored into the repository and reviewed as source —
  the checked-in copy is the pin. Staleness still applies.
- The unpinned tool runs only on a developer's machine and never in CI, a
  build image, or anything that holds credentials or produces an artifact.

## Why it happens

Adding a dependency is one command, and the manifest it edits records an
intent ("anything compatible with 4.x"), not a result — the result lives in
a lockfile that is easy to leave uncommitted, let drift, or bypass with the
install command that re-resolves instead of the one that obeys. Transitive
dependencies arrive unreviewed and outnumber direct ones many times over.
Tags, branches, and `latest` look like versions but are mutable pointers
the publisher can move. And CI configuration, Dockerfiles, and install
scripts are not thought of as dependency declarations at all, so they are
held to no pinning standard even though they run with the most privilege.

## Detection smells

- A manifest changed with no corresponding lockfile change, a lockfile
  missing or ignored by version control for a deployed application, or a
  lockfile diff far larger than the manifest change explains.
- CI, Dockerfile, or deploy scripts using the resolving install
  (`install`, `update`, `get -u`) instead of the frozen one that fails
  when the lockfile and manifest disagree.
- Dependencies declared by mutable reference: a git branch, a tag, a URL
  with no hash, `latest`, `*`, or an open-ended range with no lockfile
  behind it.
- A newly added package whose name is one edit away from a popular one,
  that has few releases or downloads, or that was published very recently
  — verify the name against the upstream project's own documentation
  before accepting it (typosquatting).
- An internal package name with no scope/namespace or registry mapping
  pinning it to the private registry, in a build that also consults a
  public registry — whoever publishes that name publicly wins the
  resolution (dependency confusion).
- A package suggested by generated code or a tutorial that cannot be found
  in the registry, or exists only as a recent, empty-looking upload —
  confirm it exists and is the intended project before installing.
- Install-time code execution left on by default for untrusted packages
  (post-install scripts, build hooks) in an environment holding secrets.
- Third-party CI actions, reusable workflows, or base images referenced by
  tag rather than commit SHA or image digest — especially in jobs with
  write permissions or secrets in scope.
- Remote content fetched and executed during build or deploy — piping a
  download into a shell, an unversioned installer URL, a binary pulled
  without a checksum comparison.
- Front-end scripts or styles loaded from a third-party CDN without a
  subresource-integrity hash.
- No vulnerability scan in CI, or scan findings suppressed wholesale.
  When checking for known-vulnerable versions, run the ecosystem's audit
  tool against the lockfile; do not assert a CVE from memory.
- Dependencies that are abandoned, deprecated, or pinned years behind a
  supported release on a security-relevant path (auth, crypto, parsing,
  HTTP).

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Lockfile, frozen install, and audit tool                                                                                               |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Gemfile.lock`; `bundle install` with `BUNDLE_FROZEN`/`--deployment`; `bundler-audit`; `git:`/`branch:` gems are mutable                |
| Laravel      | `composer.lock`; `composer install` (never `update`) in CI; `composer audit`; `dev-main` constraints are mutable                        |
| Django       | hashed requirements (`pip install --require-hashes`), pip-tools/Poetry/uv lockfiles; `pip-audit`; `--extra-index-url` invites confusion |
| Spring       | Gradle dependency locking + verification metadata, Maven Enforcer; `LATEST`/`RELEASE`/ranges are mutable; OWASP Dependency-Check        |
| Node/Express | `package-lock.json` + `npm ci` (or `--frozen-lockfile`); `npm audit`; `--ignore-scripts`; scoped registries in `.npmrc`                 |
| Vapor        | committed `Package.resolved`; `.exact`/`from:` vs `branch:` requirements; `swift package resolve` vs `update`                           |
| .NET         | `packages.lock.json` + `RestoreLockedMode`; `dotnet list package --vulnerable`; `packageSourceMapping` in `nuget.config`                |
| Go           | `go.sum` + `-mod=readonly`; `govulncheck`; `replace` directives and `GOPRIVATE`/`GONOSUMDB` scope what skips the checksum database      |

## Example

Vulnerable shape:

```text
manifest:
    web-framework   = "^4.0"                # range; lockfile not committed
    acme-internal   = "*"                   # unscoped; public registry also consulted
    http-helper     = git "main"            # mutable branch

build:
    FROM runtime:latest                     # mutable tag
    run "curl https://get.tool.example/install.sh | sh"
    run package-manager install             # re-resolves on every build

ci:
    uses some-org/deploy-action@v2          # movable tag, job holds deploy secrets
```

Fixed shape — every input resolved once, recorded, and verified:

```text
manifest + committed lockfile:
    web-framework   = "^4.0"                # lockfile pins 4.2.1 + hash
    @acme/internal  = "1.8.0"               # scope mapped to the private registry
    http-helper     = "2.3.0"               # released version, hash in lockfile

build:
    FROM runtime@sha256:9c1e...             # digest
    run download tool-1.4.2 ; verify sha256 == recorded ; install
    run package-manager install --frozen    # fails if lockfile is stale

ci:
    uses some-org/deploy-action@3f9a2c...   # commit SHA (comment: v2.1.0)
    run package-manager audit               # known-vulnerability gate
```

## Severity guidance

- **Critical** — a build that can be made to install attacker-published
  code today: an internal name resolvable from a public registry, a
  package that is confirmed to be a typosquat, or unverified remote code
  executed in a job holding production credentials. Also a known
  vulnerability with a demonstrated reachable path to code execution or
  authentication bypass.
- **High** — a deployed application with no committed lockfile or whose
  build ignores it; a third-party CI action or image on a mutable
  reference in a job with secrets or write permissions; a known
  vulnerability on a reachable path gated by a real precondition.
- **Medium** — a known-vulnerable version with no demonstrated reachable
  path; mutable base-image tags or missing subresource integrity; install
  scripts enabled for a large unreviewed tree; no vulnerability scan.
- **Low** — platform-vendor actions pinned by major tag, unpinned
  development-only tooling, stale but unaffected dependencies; flag as
  hardening.
