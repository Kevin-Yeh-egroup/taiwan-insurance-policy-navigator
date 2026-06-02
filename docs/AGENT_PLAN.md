# Agent Discussion Plan

## Routing

Task type: Knowledge + Engineering + Frontend + Publishing governance.

Done means: a local git repo contains a usable static web app, source index, crawler scripts, research-backed information architecture, validation checks, and a clear approval gate for GitHub/Vercel production.

Agents used:

- `task_router`: split the work into research, source extraction, app build, crawler, and publish gates.
- `context_scout`: researched better insurance information organization patterns.
- `doc_scribe`: converted research into IA and docs.
- `engineering_reviewer`: scoped crawler, data validation, and repository safety.
- `frontend_qa`: verifies the dashboard and mobile layout.
- `risk_guardian`: controls public repo, Vercel, noindex, crawler etiquette, and legal/claim wording.

## Multi-Agent Conclusions

The site should not be a PDF warehouse. The primary reader flow should answer:

- What does it cover?
- What may trigger or block a claim?
- Which definitions matter?
- What are the waiting period and exclusions?
- What does renewal/premium status depend on?
- What original document supports this summary?

## Phased Execution

### Phase 1 - Local Repository And Evidence

- Extract URLs from provided files.
- Remove local/private URLs from public crawl queue.
- Create public-safe source index.
- Build static dashboard and source explorer.
- Run a small polite crawl status batch.

### Phase 2 - Structured Policy Extraction

- Crawl official product pages and PDFs in batches.
- Parse document titles, approval/version dates, file hashes, and product names.
- Extract consumer fields with source clauses and confidence status.
- Mark stale/missing/changed documents.

### Phase 3 - Review And Production

- Run data validation and browser QA.
- Confirm no legal/claim promise language.
- Ask Kevin to approve public repo and Vercel Production.
- Push to GitHub, connect Vercel, verify `200 OK`, `robots.txt`, meta robots, and `X-Robots-Tag`.
