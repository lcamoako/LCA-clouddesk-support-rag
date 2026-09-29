---
source_type: api_documentation
title: "Webhooks Reference"
doc_id: API-WEBHOOK-01
last_updated: 2026-07-14
version: "v3.6"
audience: developer
---

# Webhooks Reference

Webhooks let your application receive real-time notifications when events occur in CloudDesk (new ticket, ticket resolved, SLA breach, customer reply, etc.).

## Configuring an endpoint

1. Go to **Settings → Developer → Webhooks → Add Endpoint**.
2. Enter a publicly reachable HTTPS URL. HTTP (non-TLS) endpoints are rejected.
3. Select the events to subscribe to.
4. CloudDesk generates a **signing secret** (`whsec_...`) shown once — store it securely.

## Payload format

```json
{
  "event": "ticket.resolved",
  "created_at": "2026-07-01T14:22:03Z",
  "webhook_id": "wh_3f9a2b",
  "data": {
    "ticket_id": "tkt_88213",
    "status": "resolved",
    "resolved_by": "agent_4471"
  }
}
```

## Verifying the signature

Every request includes an `X-CloudDesk-Signature` header: `t=<timestamp>,v1=<hex_hmac>`.

Compute `HMAC-SHA256(signing_secret, "{t}.{raw_request_body}")` and compare to `v1` using a constant-time comparison. Reject the request if the timestamp is more than 5 minutes old (replay protection).

## Retry policy

If your endpoint does not return a `2xx` status within 10 seconds, CloudDesk retries with exponential backoff:

| Attempt | Delay after previous attempt |
|---|---|
| 1 (initial) | — |
| 2 | 1 minute |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |
| 6 (final) | 12 hours |

After the 6th failed attempt, the event is marked `failed` and the webhook is automatically **disabled** if more than 20 consecutive events fail. A workspace admin must re-enable it from the Webhooks dashboard.

## Common causes of webhook failures

1. **Endpoint returns non-2xx or times out** — check application logs for exceptions during processing; ensure the handler responds before doing slow downstream work (acknowledge first, process asynchronously).
2. **TLS certificate expired or self-signed** — CloudDesk's webhook sender validates certificates and will not deliver to endpoints with invalid TLS.
3. **Signature verification mismatch** — usually caused by re-serializing the JSON body before verifying (whitespace/key-order changes the byte string). Verify against the *raw* request body, not a re-parsed object.
4. **Firewall/IP allowlist blocking CloudDesk's sending IPs** — see the current IP ranges at `/v1/meta/webhook-ips`.
5. **Endpoint URL changed without updating CloudDesk** (e.g., after a load balancer migration) — returns connection refused/DNS errors.
6. **Payload size limit exceeded** — bulk events (e.g., `tickets.bulk_updated`) are capped at 512 KB; oversized payloads are chunked into multiple deliveries with a `page` field.

## Manually replaying failed events

`POST /v1/webhooks/{webhook_id}/events/{event_id}/replay` — replays a single event. Replayed events carry the original `created_at` but a new `webhook_id` delivery attempt ID.

## Related resources
- Help Center: "Troubleshooting Failed Webhook Deliveries" (HC-102)
- Runbook: "Webhook Delivery Failure Response"
