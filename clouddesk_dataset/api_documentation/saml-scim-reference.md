---
source_type: api_documentation
title: "SAML & SCIM Configuration Reference"
doc_id: API-SSO-01
last_updated: 2026-07-28
version: "v3.6"
audience: developer
---

# SAML & SCIM Configuration Reference

Technical reference for administrators wiring an Identity Provider (IdP) — Okta, Azure AD, OneLogin, Google Workspace — to CloudDesk via SAML 2.0, plus SCIM for automated user provisioning.

## SAML metadata

CloudDesk's Service Provider (SP) metadata is available per-workspace at:

```
GET https://auth.clouddesk.io/saml/{workspace_id}/metadata.xml
```

Key attributes your IdP must map:

| SAML Attribute | Maps to | Required |
|---|---|---|
| `NameID` (email format) | User email | Yes |
| `firstName` | Given name | No |
| `lastName` | Family name | No |
| `department` | Team assignment (if team-mapping enabled) | No |

## Domain verification

SAML is enforced **per verified domain**, not per workspace. Before SSO applies to a domain, it must be verified:

1. `POST /v1/sso/domains` with `{ "domain": "acme.com" }` returns a TXT record to add to DNS.
2. CloudDesk polls DNS every 15 minutes for up to 24 hours.
3. Once verified, `domain.status` becomes `active`.

**Important:** adding a *new* domain to a workspace that already has SSO enabled does **not** automatically enforce SSO on that new domain. Each domain requires its own verification and an explicit `enforce_sso: true` flag via `PATCH /v1/sso/domains/{domain_id}`. Until that flag is set, users on the new domain can still log in with a password, which is a common source of "SSO stopped working" reports — the more frequent underlying cause is actually the *original* domain's certificate expiring around the same time a new domain was added, not the new domain itself.

## Certificate expiry

IdP signing certificates are commonly rotated on a 1–3 year cycle. CloudDesk does **not** auto-renew IdP certificates — an expired cert causes all SAML logins for that domain to fail with `saml_signature_invalid` until an admin uploads the renewed certificate at `Settings → Security → SSO → Identity Provider Certificate`.

## SCIM provisioning

Base URL: `https://api.clouddesk.io/scim/v2`

Supports `Users` and `Groups` resources per the SCIM 2.0 spec. Deactivating a user via SCIM (`active: false`) revokes all active sessions within 5 minutes.

## Common error codes

| Code | Meaning | Typical fix |
|---|---|---|
| `saml_signature_invalid` | Certificate mismatch or expired | Re-upload current IdP certificate |
| `saml_domain_not_verified` | NameID domain has no active verification | Complete domain verification |
| `saml_clock_skew` | IdP and SP clocks differ by >5 minutes | Sync IdP server time (NTP) |
| `scim_duplicate_external_id` | Two users provisioned with same externalId | De-duplicate in IdP directory |

## Related resources
- Help Center: "Setting Up Single Sign-On (SSO) with SAML" (HC-103)
- Runbook: "SSO/SAML Authentication Outage Response"
