---
source_type: engineering_runbook
title: "SSO/SAML Authentication Outage Response"
doc_id: RB-SSO-01
last_updated: 2026-08-01
version: "v3.6"
severity_scope: SEV3-SEV1
audience: internal (engineering / support escalation)
---

# Runbook: SSO/SAML Authentication Outage Response

## Trigger conditions

- Multiple users at one workspace cannot log in via SSO.
- Alert: `saml_login_failure_rate` for a workspace exceeds 30% over 5 minutes.
- Customer ticket containing phrases like "SSO stopped working", "SAML login broken", or "can't log in after adding a domain".

## Triage (first 5 minutes)

1. Pull the workspace's recent SAML error codes from `admin/sso/{workspace_id}/errors`.
2. Match the dominant error code to a path below. **Do not assume the most recently changed configuration (e.g., a newly added domain) is the cause** — in historical incidents, certificate expiry on the *original*, previously-working domain has been the actual trigger more often than the new domain itself, because admins tend to touch SSO settings around the same time a cert is due to expire.

## Resolution paths by error code

### `saml_signature_invalid`
- Check IdP certificate expiry: `admin/sso/{workspace_id}/certificate`. This is the single most common cause of sudden SSO outages.
- If expired: ask the workspace admin to download a fresh signing certificate from their IdP and re-upload it at Settings → Security → SSO.
- If not expired: confirm the IdP hasn't rotated certificates without notice (common with Azure AD's automatic rollover) — request the current cert directly from the IdP admin console.

### `saml_domain_not_verified`
- Check `admin/sso/{workspace_id}/domains` for the affected domain's status.
- If a domain was recently added and is `pending`, this is expected — DNS verification takes up to 24 hours. Direct the customer to confirm the TXT record is published.
- Remind the customer that `enforce_sso` must be explicitly set per domain; adding a new domain never auto-enforces SSO on it.

### `saml_clock_skew`
- Ask the customer to confirm their IdP server's NTP sync. CloudDesk allows a 5-minute skew tolerance; anything beyond that fails.

### `scim_duplicate_external_id`
- This affects provisioning, not login. Direct to the SCIM directory to de-duplicate the conflicting user record.

## Communication

- For any outage affecting more than 10 users at one workspace, post a status update in `#customer-comms` within 15 minutes so support agents have a holding message before the RAG assistant's confidence threshold routes tickets to them.

## Escalation

- SEV1 if SSO is down for an Enterprise-tier workspace during business hours (per their timezone) — page Identity Platform on-call immediately.
- SEV2/3 for smaller workspaces or after-hours — handle within the current shift.

## Related resources
- API doc: `saml-scim-reference.md`
- Help Center: "Setting Up Single Sign-On (SSO) with SAML" (HC-103)
