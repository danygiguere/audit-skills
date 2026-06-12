# Tenant Isolation

## Invariant

In multi-tenant code, every database query, cache key, file path, search
call, and background job is explicitly scoped to one tenant, with the tenant
derived from server-side context (the authenticated principal), never from
the request alone. Any deliberately cross-tenant code path is visibly marked
as such.

## Does not apply when

- The application is genuinely single-tenant — one organization per
  deployment, with isolation handled at the infrastructure level.

## Why it happens

Tenancy is a column, and columns are easy to omit from WHERE clauses —
especially on detail and update paths, where find-by-primary-key already
returns exactly one row and looks complete. Caches, job queues, and search
indexes sit outside the ORM, where automatic scoping (global scopes, default
querysets) does not reach. Legitimate cross-tenant admin and reporting code
normalizes unscoped queries, which then get copied into tenant-facing paths.

## Detection smells

- A detail, update, or delete endpoint fetches by primary key alone while
  the sibling list endpoint filters by tenant.
- Queries that bypass the scoping layer: raw SQL, query-builder escapes, or
  ORM calls flagged to skip default scopes.
- Cache get/set keys built without a tenant component (`user:42`,
  `settings:report`) in code serving multiple tenants.
- A background job iterates over tenants while carrying shared mutable state
  across iterations — memoized config, a "current tenant" global,
  connection-level settings.
- Job payloads carry record IDs but no tenant, and the worker resolves the
  records globally.
- Uniqueness or existence checks that run globally ("email already
  registered", slug collision) and thereby confirm other tenants' data.
- Tenant identity taken from a request-controlled value (header, body,
  arbitrary subdomain) without verifying the principal belongs to that
  tenant.
- Tenant scoping added to one query or handler but absent from sibling
  paths touching the same table or cache — scope parity across peers is
  part of the invariant.

## Concept glossary

*Recognition vocabulary, not a support list — this checklist applies to any language or framework; these rows just name the concept in common ecosystems.*

| Ecosystem    | Where scoping usually lives                                                                                                                       |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Rails        | `acts_as_tenant`/`default_scope` + `Current.tenant`; escape hatch: `unscoped`                                                                     |
| Laravel      | global scopes (tenant trait), stancl/tenancy; escape hatch: `withoutGlobalScopes`                                                                 |
| Django       | custom managers filtering by tenant, django-tenants (schema-per-tenant); escape hatch: base manager `objects`                                     |
| Spring       | Hibernate `@TenantId`/filters, tenant-routed datasources; escape hatch: native queries                                                            |
| Node/Express | middleware puts tenant on request context; every query needs `WHERE tenant_id = ?` — nothing is automatic                                         |
| Vapor        | tenant filter on every Fluent query (`filter(\.$tenant.$id == ...)`); tenant resolved in middleware; `req.cache` keys include the tenant          |
| .NET         | EF Core global query filters (`HasQueryFilter(e => e.TenantId == tenant)`); `IgnoreQueryFilters()` is the bypass smell; cache keys include tenant |
| Go           | tenant ID carried in `context.Context` into every query; tenant-scoped repository constructors; GORM scopes                                       |

## Example

Vulnerable shape:

```text
handler get_report(request):
    report = db.reports.find(request.params.id)     # any tenant's report
    cached = cache.get("report:" + report.id)       # key collides across tenants
    respond json(report)
```

Fixed shape — tenant from server-side context, scoped lookup, tenant-keyed
cache; a foreign ID behaves like a nonexistent one:

```text
handler get_report(request):
    tenant = request.principal.tenant_id            # never from the request body
    report = db.reports.find_where(id = request.params.id, tenant = tenant)
    if report is null: respond 404
    cached = cache.get("t:" + tenant + ":report:" + report.id)
    respond json(report)
```

## Severity guidance

- **Critical** — cross-tenant write or delete; read of another tenant's
  credentials/financial/health data; tenant identity trusted from the
  request.
- **High** — cross-tenant read of business data; cache leakage or poisoning
  across tenants.
- **Medium** — existence/metadata leaks (global uniqueness checks);
  cross-tenant state bleed in jobs without direct data exposure.
- In B2B products, treat any confirmed cross-tenant leak as at least High —
  a single incident is contract-level.

## Remediation

See `../remediation/authz-patterns.md` — tenant-scoped query layers, scoped
lookups, and deny-by-default scoping.
