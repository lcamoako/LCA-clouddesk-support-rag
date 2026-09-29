# CloudDesk AI Support Engineer — Sample RAG Dataset

This is a realistic, internally-consistent dataset built to match the 5 source types defined in the
CloudDesk AI Support Engineer case (Section 5.2):

| Folder | Format | Files | Role |
|---|---|---|---|
| `help_center_articles/` | PDF | 5 | Customer-facing how-to / troubleshooting content |
| `api_documentation/` | Markdown (.md) | 4 | Developer-facing integration & endpoint reference |
| `support_tickets/` | CSV | 1 file, 43 rows | Historical Q&A pairs for grounding |
| `engineering_runbooks/` | Markdown (.md) | 3 | Internal incident-response procedures |
| `release_notes/` | PDF | 3 | Version history (v3.4.0 → v3.6.0) |

## Why the content is built this way

The five sources are **cross-referenced on purpose**, the way a real SaaS knowledge base is:

- Each Help Center article ends with a "Related" pointer to the matching API doc and/or runbook.
- Each API doc's frontmatter and "Related resources" section links back to its Help Center article and runbook.
- Each runbook cites the API doc it operationalizes.
- The support tickets CSV's `source_type_reference` / `source_title_reference` columns show, per ticket,
  which document *would* have grounded the answer — this simulates the "previous tickets" ingestion path
  and gives you ground truth for evaluating retrieval quality (Step 7 in the case: Evaluation & Testing).

This lets a RAG pipeline actually demonstrate multi-source retrieval and citation, rather than each
document living in isolation.

## A worked example matching the case's own scenario

The case document uses this example: *"My SAML login stopped working after adding a new domain."*
This dataset deliberately builds out the **real root cause behind that scenario** across three sources so
you can test whether your RAG pipeline retrieves the correct explanation instead of the naive one:

- `help_center_articles/HC-103_setting-up-sso-with-saml.pdf` — tells the customer the likely cause is an
  expired IdP certificate on the *original* domain, not the new domain.
- `api_documentation/saml-scim-reference.md` — gives the technical detail: domain verification and
  `enforce_sso` are separate, per-domain steps.
- `engineering_runbooks/runbook-sso-saml-incident-response.md` — instructs engineers/support agents not
  to assume the most-recently-changed config is the cause.
- `support_tickets/previous_support_tickets.csv` (ticket `tkt_10034`) — a resolved historical ticket with
  exactly this complaint and the correct resolution.

This is a good test case for the confidence-scoring objective (Objective 3): a shallow retrieval that only
matches on "new domain" should surface a lower-confidence, incomplete answer; a good pipeline should pull in
the certificate-expiry explanation from at least two of the four sources above.

## Metadata schema

Per Section 5.3, every document carries: `source_type`, `title`, `chunk_id` (assign at ingestion/chunking
time — not pre-set here), `last_updated`, `version`. The Markdown files carry this as YAML frontmatter; the
PDFs carry it as a metadata line under the title on page 1. Apply your PDF/Markdown loaders accordingly
(see Step 2 of the project workflow).

## Suggested next steps for the RAG pipeline

1. **Ingestion**: PDF loader for `help_center_articles/` and `release_notes/`; Markdown splitter for
   `api_documentation/` and `engineering_runbooks/` (split on `##` headers works well here); CSV loader for
   `support_tickets/`, treating each row as one chunk (`customer_question` + `agent_answer` concatenated).
2. **Chunking**: PDFs chunk cleanly by `H2`/`H3` heading; keep the metadata line attached to every chunk
   from that document.
3. **Evaluation set**: Use the 43 ticket rows as a held-out test set — for each `customer_question`, check
   whether retrieval surfaces the document named in `source_type_reference` / `source_title_reference`,
   and whether the generated answer matches the spirit of `agent_answer`.
4. **Confidence scoring test cases**: Tickets with ambiguous or multi-cause answers (e.g. `tkt_10034`,
   `tkt_10051`, `tkt_10121`) are good candidates for checking the <60% escalation threshold behaves
   correctly on genuinely hard cases, versus straightforward ones (e.g. `tkt_10052`, `tkt_10061`) that
   should score confidently high.
