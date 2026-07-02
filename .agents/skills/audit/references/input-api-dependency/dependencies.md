# Dependencies & Supply Chain

## Invariant

Every third-party package is deliberately chosen, pinned to an exact,
reviewed version through a committed lockfile, and resolved from the
registry the team intends. Builds install from the lockfile
reproducibly — the code that was reviewed is the code that ships. Install
hooks and new packages are treated as arbitrary code execution with the
installing user's credentials, because that is what they are. A dependency
change is a code change: it gets the same review as one.

## Does not apply when

- The "dependency" is an internal workspace/monorepo package built from
  source in the same repository — it is already reviewed code.
- The change only moves versions **within** an already committed lockfile
  via the ecosystem's own update tooling, with the diff visible for review.

## Why it happens

Adding a package is one command, and the resulting lockfile diff is a blob
nobody reads — so a transitive tree of unreviewed code lands invisibly.
Version ranges (`^`, `>=`, `latest`) mean tomorrow's install differs from
today's review. Public registries resolve names globally: a typo lands on
an attacker's package, and an internal package name that was never claimed
publicly can be shadowed with a higher version (dependency confusion).
Install scripts run at fetch time — before the code is ever imported — with
developer and CI credentials in scope. And once a package is in, nothing
prompts anyone to notice it is abandoned or newly vulnerable.

## Detection smells

- A manifest change (`package.json`, `Gemfile`, `go.mod`, …) without the
  corresponding lockfile change — or a lockfile deleted/regenerated
  wholesale to "fix conflicts", burying what actually moved.
- CI or Dockerfiles installing with the resolving command (`npm install`,
  `bundle update`, `pip install -r` on unpinned ranges) instead of the
  reproducing one (`npm ci`, `bundle install` with frozen lockfile,
  hash-checked requirements).
- Floating direct dependencies: `*`, `latest`, bare `>=`, a git URL pinned
  to a branch instead of a commit SHA, tarballs fetched over plain HTTP.
- A new package whose name is one edit away from a popular one, published
  days ago, with trivial download counts or no repository link — pulled in
  for something the standard library or an existing dependency already does.
- Internal package names resolvable from the public registry: no scoped
  namespace (`@org/`), no claimed placeholder, a registry config that mixes
  private and public indexes with public fallback
  (`--extra-index-url`-style resolution).
- New or updated packages carrying install/post-install hooks that nobody
  read; CI installing untrusted trees without disabling script execution;
  deploy/publish credentials present in the environment during install.
- A pinned version with a known CVE silenced (audit exception, ignore file)
  without a recorded justification or an upgrade path.
- No automated signal at all: no lockfile audit, no Dependabot/Renovate or
  ecosystem-equivalent watching the tree — vulnerable versions have no way
  to surface.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Reproducible install vs the trap                                                                                                 |
|--------------|------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `Gemfile.lock` committed + `bundle config set frozen true` in CI vs `bundle update` in the build; `bundler-audit`                  |
| Laravel      | `composer.lock` committed + `composer install` in CI vs `composer update`; `composer audit`; roave/security-advisories             |
| Django       | hash-pinned requirements (`pip install --require-hashes`) or `poetry.lock`/`uv.lock` vs bare `requirements.txt` ranges; `pip-audit` |
| Spring       | fixed versions/BOM + Gradle dependency locking or Maven enforcer vs dynamic `latest.release`; OWASP dependency-check              |
| Node/Express | `package-lock.json` + `npm ci` vs `npm install` in CI; `npm audit`; `--ignore-scripts` for untrusted trees; scoped `@org/` names   |
| Vapor        | `Package.resolved` committed + exact/`upToNextMinor` ranges vs `branch:`-based SwiftPM dependencies                                |
| .NET         | `packages.lock.json` + `RestorePackagesWithLockFile`/locked mode vs floating `*` PackageReference; `dotnet list package --vulnerable` |
| Go           | `go.mod` + `go.sum` (hash-verified by default) + `GOPROXY`/`GONOSUMDB` deliberate vs `GOFLAGS=-mod=mod` drift; `govulncheck`       |

## Example

Vulnerable shape — a manifest diff that ships unreviewed, mutable code:

```text
# manifest diff under review
+ "http-utils":  "github:someuser/http-utils#main"   # branch ref — mutable
+ "left-padd":   "^1.0.0"                             # typosquat, floating range
# lockfile: not part of the diff; CI runs `npm install` (re-resolves at build)
```

Fixed shape — pinned, lock-checked, scripts contained:

```text
# manifest diff under review
+ "http-utils": "github:someuser/http-utils#9f2c1e4b"   # immutable commit SHA
+ "left-pad":   "1.3.0"                                  # intended name, exact pin
# lockfile committed in the same change; reviewer sees the resolved tree
# CI: `npm ci --ignore-scripts` — reproduces the lockfile, no install hooks
```

## Severity guidance

- **Critical** — an internal package name resolvable from a public
  registry (dependency confusion), or a new package whose install hook runs
  in CI/dev environments holding deploy or publish credentials: arbitrary
  code execution in the supply chain.
- **High** — a deployed service building without a committed lockfile or
  with floating direct versions (unreviewed code reaches production on the
  next build); adding a version with a known exploitable CVE on a reachable
  path.
- **Medium** — typosquat-risk or unmaintained packages for
  security-relevant functions; lockfile present but CI uses the resolving
  installer; CVE exceptions without justification.
- **Low** — redundant dependencies that widen the surface; dev-only
  dependency hygiene; missing automated audit signal with an otherwise
  pinned tree.
