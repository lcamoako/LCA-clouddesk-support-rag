---
source_type: api_documentation
title: "Authentication"
doc_id: API-AUTH-01
last_updated: 2026-06-02
version: "v3.6"
audience: developer
---

# Authentication

CloudDesk's REST API supports two authentication methods: **API Keys** (recommended for server-to-server integrations) and **OAuth 2.0** (recommended for third-party apps acting on behalf of a user).

## 1. API Key Authentication

Every CloudDesk workspace can generate API keys from **Settings → Developer → API Keys**. Keys are scoped to a workspace and inherit the permissions of the role that created them.

### Making an authenticated request

Include the key in the `Authorization` header as a Bearer token:

```
GET /v1/tickets HTTP/1.1
Host: api.clouddesk.io
Authorization: Bearer cd_live_8f2a1c9e4b7d4e2a9c1f0a6b3d7e9f10
```

### Key types

| Prefix | Environment | Notes |
|---|---|---|
| `cd_live_` | Production | Full access per role permissions |
| `cd_test_` | Sandbox | Data isolated from production workspace |

### Rate limits

- Standard plan: 60 requests/minute per key
- Growth plan: 300 requests/minute per key
- Enterprise plan: 1,200 requests/minute per key

Exceeding the limit returns `HTTP 429 Too Many Requests` with a `Retry-After` header (seconds). Implement exponential backoff; do not retry immediately on a 429.

### Key rotation

Old keys remain valid for 24 hours after a new key is generated, to allow zero-downtime rotation. Revoking a key immediately invalidates it — in-flight requests using a revoked key return `401 Unauthorized`.

## 2. OAuth 2.0 (Authorization Code flow)

Used for public apps (e.g., Slack, marketplace integrations) that need to act on behalf of a CloudDesk user.

1. Redirect the user to `https://auth.clouddesk.io/oauth/authorize` with `client_id`, `redirect_uri`, `scope`, and `state`.
2. User approves the requested scopes.
3. CloudDesk redirects back to `redirect_uri` with an authorization `code`.
4. Exchange the code at `POST https://auth.clouddesk.io/oauth/token` for an `access_token` (expires in 1 hour) and `refresh_token` (expires in 90 days).

### Common OAuth errors

| Error | Cause | Fix |
|---|---|---|
| `invalid_scope` | Requested scope not enabled for the app | Enable scope in app registration or request a narrower scope |
| `redirect_uri_mismatch` | Callback URL doesn't exactly match registered URI | Ensure exact match, including trailing slash and protocol |
| `invalid_grant` | Authorization code expired (codes expire after 60 seconds) or already used | Restart the authorization flow |

## 3. Signature verification for inbound webhooks

See `webhooks-reference.md` — webhook payloads are authenticated differently from outbound API calls (HMAC signature, not Bearer token).

## Related resources
- Help Center: "Managing API Keys and Rate Limits" (HC-104)
- Runbook: "API & Database Latency Incident Response"
