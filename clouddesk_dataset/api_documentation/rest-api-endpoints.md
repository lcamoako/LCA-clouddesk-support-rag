---
source_type: api_documentation
title: "REST API Endpoints Overview"
doc_id: API-CORE-01
last_updated: 2026-05-20
version: "v3.5"
audience: developer
---

# REST API Endpoints Overview

Base URL: `https://api.clouddesk.io/v1`

## Tickets

| Method | Path | Description |
|---|---|---|
| GET | `/tickets` | List tickets, filterable by `status`, `assignee`, `created_after` |
| GET | `/tickets/{id}` | Retrieve a single ticket with full conversation thread |
| POST | `/tickets` | Create a ticket |
| PATCH | `/tickets/{id}` | Update status, priority, or assignee |
| POST | `/tickets/{id}/replies` | Add a reply to a ticket |

## Customers

| Method | Path | Description |
|---|---|---|
| GET | `/customers` | List customers |
| GET | `/customers/{id}` | Retrieve customer profile and ticket history |
| POST | `/customers` | Create a customer record |

## Agents & Teams

| Method | Path | Description |
|---|---|---|
| GET | `/agents` | List agents and their current ticket load |
| GET | `/teams/{id}` | Retrieve team routing rules |

## Pagination

All list endpoints use cursor pagination: `?limit=50&cursor=<opaque_token>`. The response includes `next_cursor`; pass it back to fetch the next page. `limit` max is 100.

## Errors

Errors follow a consistent envelope:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Ticket tkt_00000 does not exist in this workspace.",
    "request_id": "req_7a2c9e"
  }
}
```

Include `request_id` when contacting support about an API error.

## Related resources
- `authentication.md` — how to authenticate requests
- `webhooks-reference.md` — real-time event notifications instead of polling
