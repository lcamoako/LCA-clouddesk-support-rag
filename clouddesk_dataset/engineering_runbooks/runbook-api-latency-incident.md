---
source_type: engineering_runbook
title: "API & Database Latency Incident Response"
doc_id: RB-API-01
last_updated: 2026-04-22
version: "v3.4"
severity_scope: SEV3-SEV1
audience: internal (engineering / support escalation)
---

# Runbook: API & Database Latency Incident Response

## Trigger conditions

- `p95 API latency > 2s` sustained for 5+ minutes.
- Customers report `429` errors despite being under their documented rate limit.
- Ticket queue-server dashboard shows elevated read latency on the primary ticket database.

## Triage

1. Check `admin/infra/db-primary` for replication lag and connection pool saturation.
2. Check whether a specific workspace is generating disproportionate load (`admin/infra/top-workspaces-by-qps`) — a single customer running an unthrottled bulk sync is the most common root cause.
3. Confirm whether the rate limiter is misfiring: compare the customer's reported 429s against their actual logged request volume in `admin/infra/rate-limit-audit/{workspace_id}`. A mismatch usually indicates the limiter is keying on the wrong identifier after a recent deploy (e.g., keying by IP instead of API key behind a shared NAT).

## Resolution paths

### Single workspace overloading shared infrastructure
- Apply a temporary per-workspace throttle via `admin/infra/throttle/{workspace_id}`.
- Contact the customer's technical owner to recommend batching or using cursor pagination with larger `limit` values instead of tight polling loops.

### Rate limiter misconfiguration
- Roll back the most recent rate-limiter deploy if the timing correlates.
- Manually clear affected customers' rate-limit counters via `admin/infra/rate-limit-reset/{workspace_id}` once the fix is confirmed.

### Database replication lag
- Check for a long-running migration or backfill job; pause non-critical batch jobs first.
- If lag exceeds 60 seconds, page the Data Platform on-call.

## Escalation

- SEV1 if the primary API is returning elevated 5xx rates platform-wide.
- SEV2 if isolated to specific endpoints or a subset of workspaces.

## Related resources
- API doc: `authentication.md` (rate limit table)
- API doc: `rest-api-endpoints.md`
