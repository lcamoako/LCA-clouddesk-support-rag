---
source_type: engineering_runbook
title: "Webhook Delivery Failure Response"
doc_id: RB-WEBHOOK-01
last_updated: 2026-07-16
version: "v3.6"
severity_scope: SEV3-SEV2
audience: internal (engineering / support escalation)
---

# Runbook: Webhook Delivery Failure Response

## Trigger conditions

- Customer reports webhooks not arriving, or arriving late.
- Internal alert: `webhook_dead_letter_queue_depth > 500` for 10+ minutes (PagerDuty: `#webhooks-oncall`).
- Spike in `webhook.delivery.failed` events in the delivery-service dashboard.

## Triage (first 5 minutes)

1. Check the **delivery-service** health dashboard (Grafana → `webhook-delivery`) for elevated latency or error rate on the *sending* side. If the sender itself is degraded, this is a platform incident — page the on-call SRE, skip to step 5.
2. If the sender is healthy, the failure is almost always on the **customer's receiving endpoint**. Pull the affected `webhook_id` and inspect the last 10 delivery attempts via internal tool `admin/webhooks/{id}/attempts`.
3. Classify the failure using the HTTP status / error captured on the attempt:
   - `timeout` / connection refused → endpoint down or unreachable
   - `4xx` → endpoint rejecting the payload (auth, malformed request, or the customer's signature verification failing)
   - `5xx` → customer's server erroring while processing
   - TLS handshake failure → expired/invalid certificate on customer endpoint

## Resolution paths

### Customer endpoint is down or timing out
- Confirm with the customer that their receiving service is up.
- If it was down for < 12 hours (before the 6-attempt retry window exhausted), the events will redeliver automatically — no action needed once their endpoint recovers.
- If more than 20 consecutive events failed, the webhook was **auto-disabled**. Re-enable via `admin/webhooks/{id}/enable` once the customer confirms their endpoint is fixed, then instruct them to use `POST /v1/webhooks/{id}/events/{event_id}/replay` for any events they need re-sent (see API doc `webhooks-reference.md`).

### Signature verification failures reported by customer
- This is almost always caused by the customer verifying against a re-serialized JSON body rather than the raw request bytes. Point them to the "Verifying the signature" section of `webhooks-reference.md`.
- Confirm they're using the current signing secret — secrets rotate if the customer regenerated them and didn't update their code.

### TLS certificate errors
- CloudDesk will not deliver to endpoints with expired or self-signed certs. This is by design, not a bug. Direct customer to renew/replace their certificate.

### Platform-side sender degradation (rare)
1. Page `#webhooks-oncall`.
2. Check whether the vector-DB-backed metadata lookup service (used to fetch per-endpoint config) is the bottleneck — this has been the root cause in 2 of the last 3 sender-side incidents.
3. If confirmed, fail over to the standby delivery-service region per the platform failover runbook (separate doc).
4. Once resolved, the dead-letter queue drains automatically; do not manually replay in bulk until sender health is confirmed stable for 15 minutes (bulk replay during instability can re-trigger the same failure).

## Escalation

- If unresolved after 30 minutes of triage, or if more than 5 customers are affected simultaneously, escalate to Platform Engineering on-call and open a SEV2 incident.

## Related resources
- API doc: `webhooks-reference.md`
- Help Center: "Troubleshooting Failed Webhook Deliveries" (HC-102)
