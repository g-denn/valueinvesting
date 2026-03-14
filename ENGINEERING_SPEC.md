# Idea Radar for Value Investing — Engineering Spec (MVP)

## 1) Scope and Product Positioning

This spec translates the PRD into an executable MVP plan.

### In scope (MVP)
- Source ingestion from:
  - Substack RSS feeds
  - Manual URL import
  - User-uploaded PDFs and pasted text
- Document parsing and normalization
- Structured thesis extraction (JSON schema)
- Quality scoring and deduplication
- Search and retrieval (ticker + semantic query)
- Weekly digest generation
- Basic UI views: feed, company page, idea card, source page, saved items
- Human-in-the-loop correction and feedback

### Out of scope (MVP)
- Portfolio automation or buy/sell decisions
- Paywall bypassing or prohibited scraping
- Generic chatbot workflows
- Full multi-modal ingestion (podcasts/video) before Phase 2

---

## 2) High-Level Architecture

Pipeline (asynchronous, event-driven):

1. **Ingestion Service**
2. **Parsing/Cleaning Service**
3. **Normalization & Metadata Service**
4. **Extraction Service** (LLM + deterministic checks)
5. **Scoring & Dedup Service**
6. **Indexing Service** (relational + vector)
7. **Retrieval/API Service**
8. **Digest/Report Service**
9. **Frontend**

### Proposed tech stack
- **Backend/API**: Python + FastAPI
- **Queue/Orchestration**: Celery + Redis (or Dramatiq)
- **DB**: PostgreSQL
- **Vector**: pgvector (MVP simplicity)
- **Object storage**: S3-compatible bucket (raw docs, parse artifacts)
- **LLM layer**:
  - small model for classification/extraction helpers
  - stronger model for synthesis/comparison tasks
- **Observability**:
  - structured logs
  - per-document trace IDs
  - dead-letter queue for failures

---

## 3) Service Boundaries and Responsibilities

## 3.1 Ingestion Service
Responsibilities:
- Poll RSS sources every N minutes
- Accept manual URL submissions
- Accept PDF/text uploads
- Enforce source policy rules (robots/terms metadata)
- Write `Document` records in `INGESTED` state

Key outputs:
- Raw payload in object store
- Ingestion metadata with retrieval method and access status

## 3.2 Parsing/Cleaning Service
Responsibilities:
- Extract main content from HTML/PDF/text
- Strip boilerplate/navigation junk
- Detect title/date/author/body
- Segment content into semantic chunks
- Mark teaser/incomplete/paywalled indicators

Key outputs:
- `clean_text`
- section/chunk table for provenance and embedding
- parse quality flags

## 3.3 Normalization & Metadata Service
Responsibilities:
- Normalize ticker formatting
- Detect company names, geography, currency, direction hints
- Identify language and doc type
- Precompute canonicalized text fingerprint inputs

## 3.4 Extraction Service
Responsibilities:
- Produce strict-schema idea card JSON
- Extract claims (catalysts/risks/valuation/etc.) with source spans
- Return confidence per field + model version
- Reject malformed output and retry with constrained prompting

## 3.5 Scoring & Dedup Service
Responsibilities:
- Compute quality dimensions:
  - specificity, evidence density, originality, clarity,
    falsifiability, valuation depth, business understanding,
    edge/variant, author track record proxy, novelty
- Compute overall score using weighted formula
- Detect duplicates and near-duplicates
- Cluster by company and thesis similarity

## 3.6 Indexing & Retrieval Service
Responsibilities:
- Upsert structured entities to Postgres
- Embed chunks + idea summaries into pgvector
- Serve keyword/ticker/semantic/hybrid search
- Support filters (date/source/region/long-short/etc.)

## 3.7 Digest/Report Service
Responsibilities:
- Weekly top-idea digest
- Company dossier
- Thesis comparison and contradiction view
- “What changed?” timeline support (basic in MVP)

---

## 4) Data Model (MVP)

Below is a practical schema sketch.

### 4.1 Core tables
- `sources`
  - `id, name, source_type, base_url, policy_tag, robots_checked_at, is_active`
- `authors`
  - `id, display_name, canonical_name, source_id(optional), profile_url`
- `documents`
  - `id, source_id, author_id, url, title, published_at, language, access_type, doc_type,
    raw_object_key, raw_text, clean_text, status, parse_flags, fingerprint, created_at`
- `document_chunks`
  - `id, document_id, chunk_index, text, start_char, end_char, token_count`
- `companies`
  - `id, name, canonical_name, sector, geography`
- `tickers`
  - `id, company_id, symbol, exchange, currency, is_primary`
- `ideas`
  - `id, document_id, company_id, direction, one_line_thesis, thesis_summary,
    quality_score, novelty_score, extraction_confidence, originality_type, created_at`
- `claims`
  - `id, idea_id, claim_type, text, confidence, evidence_chunk_ids, evidence_snippets`
- `catalysts`
  - `id, idea_id, text, horizon, confidence, evidence_chunk_ids`
- `risks`
  - `id, idea_id, text, confidence, evidence_chunk_ids`
- `valuation_claims`
  - `id, idea_id, method, text, implied_value(optional), confidence, evidence_chunk_ids`
- `clusters`
  - `id, cluster_type(company|thesis|duplicate), label, created_at`
- `cluster_members`
  - `id, cluster_id, idea_id, similarity_score`
- `user_tags`
  - `id, user_id, target_type, target_id, tag, note, created_at`
- `watchlists`
  - `id, user_id, name, created_at`
- `watchlist_items`
  - `id, watchlist_id, company_id(optional), ticker_id(optional), idea_id(optional)`
- `extraction_reviews`
  - `id, user_id, idea_id, field_name, old_value, new_value, reason, created_at`
- `digests`
  - `id, period_start, period_end, generated_at, payload_json`

### 4.2 Provenance requirements (must-have)
For each extracted field or claim, store:
- source chunk IDs/snippets
- extraction confidence
- model name/version
- extraction timestamp
- prompt template version

---

## 5) Pipeline Stages and Job Contracts

## 5.1 Job state machine (document)
`INGESTED -> PARSED -> NORMALIZED -> EXTRACTED -> SCORED -> INDEXED`

Error states:
- `FAILED_PARSE`
- `FAILED_EXTRACT`
- `FAILED_INDEX`

Retries:
- exponential backoff with max attempts per stage
- dead-letter queue after max retries

## 5.2 Stage contracts
Each stage reads immutable input + writes versioned output:
- Input references by `document_id`
- Output includes `stage_version`, `model_version` where relevant
- Never overwrite raw original source material

---

## 6) LLM Extraction Design

Use multiple narrow prompts instead of one monolithic prompt.

### 6.1 Extraction tasks
1. Document intent/classification (long/short/neutral/watchlist)
2. Ticker/company extraction + normalization hints
3. Idea card extraction (strict JSON schema)
4. Claims + evidence mapping
5. Original vs commentary classification

### 6.2 Guardrails
- strict JSON schema validation
- reject unsupported fields
- enforce “no evidence span => no claim”
- deterministic post-checks for ticker format and direction label
- confidence thresholds for auto-publish vs human review queue

---

## 7) Scoring Framework (MVP)

Dimension scores in `[0, 1]`:
- signal, depth, originality, actionability, fit, novelty, freshness

Default overall score:

`overall = 0.25*signal + 0.20*depth + 0.15*originality + 0.15*actionability + 0.10*fit + 0.10*novelty + 0.05*freshness`

### 7.1 Operational logic
- Fit defaults to neutral until user preference profile exists
- Author track record can be folded into originality/depth priors later
- User override should be stored and applied as post-score rerank

---

## 8) Deduplication and Clustering

### 8.1 Duplicate detection
- Exact hash on canonicalized text
- Near-duplicate via minhash/simhash or embedding cosine threshold
- Preserve source attribution and mark canonical/original where possible

### 8.2 Company/thesis clustering
- Company clusters by resolved `company_id`
- Thesis clusters by idea embedding similarity + shared claim patterns
- Timeline generation from `published_at` sorted within cluster

---

## 9) API Surface (MVP)

### 9.1 Ingestion
- `POST /sources/rss`
- `POST /documents/url`
- `POST /documents/upload`
- `POST /documents/paste`

### 9.2 Retrieval
- `GET /feed?filters...`
- `GET /companies/{id}`
- `GET /tickers/{symbol}`
- `GET /ideas/{id}`
- `GET /search?q=...&mode=keyword|semantic|hybrid`

### 9.3 Review and feedback
- `PATCH /ideas/{id}` (editable extracted fields)
- `POST /ideas/{id}/tags`
- `POST /reviews/extraction`

### 9.4 Reports
- `GET /digests/weekly/latest`
- `GET /companies/{id}/comparison`
- `GET /companies/{id}/contradictions`

---

## 10) UI Information Architecture (MVP)

1. **Feed**: ranked incoming ideas with filters
2. **Idea Card**: one-line thesis, bullets, catalysts/risks, confidence, evidence links
3. **Company Page**: all clustered ideas, consensus/disagreement, timeline
4. **Source Page**: source metadata and output quality trend
5. **Saved/Watchlist**: user-curated tracking set

Design principle: every key extracted statement links to evidence snippets.

---

## 11) Compliance and Source Policy

- Honor robots.txt and terms metadata
- Prefer RSS/API first
- Track `access_type`: public/subscriber/restricted
- No paywall bypass behavior
- Keep retrieval logs (method, timestamp, response code, policy tag)
- Add per-source throttling settings

---

## 12) Reliability, Performance, and SLO Targets

MVP targets:
- RSS ingest latency: <= 15 minutes
- Extraction completion from ingest: <= 5 minutes (P50)
- Search latency: <= 2 seconds (P95)
- Weekly digest generation: <= 1 minute

Operational requirements:
- idempotent workers
- replayable jobs
- stage-level metrics and alerts

---

## 13) Security and Auditability

- Multi-tenant data separation ready (even if single-user initially)
- Immutable raw source storage
- Prompt/output audit logs for extraction steps
- Role-based controls for future collaboration

---

## 14) MVP Delivery Plan (8 Weeks)

### Week 1: Foundations
- Repo scaffolding (FastAPI, worker, DB migrations)
- Core schema (`sources`, `documents`, `companies`, `ideas`, `claims`)
- Basic observability and trace IDs

### Week 2: Ingestion
- RSS polling connector
- Manual URL ingestion endpoint
- PDF/text upload pipeline
- object storage integration

### Week 3: Parsing + Normalization
- HTML/PDF parsing and cleaning
- chunking pipeline
- ticker/company candidate detection

### Week 4: Extraction v1
- strict JSON schema prompts
- idea card extraction with provenance spans
- fallback/retry logic and review queue

### Week 5: Scoring + Dedup
- scoring dimensions + overall formula
- exact + near-duplicate detection
- first-pass clustering by company

### Week 6: Search + API
- pgvector embeddings and hybrid retrieval
- feed/company/idea endpoints
- filter support

### Week 7: UI + Human Review
- feed, idea card, company page, saved items
- field edit workflows and tagging
- ranking override support

### Week 8: Digest + Hardening
- weekly digest generation
- contradiction/comparison report v1
- load/perf tuning and reliability fixes

---

## 15) Acceptance Criteria (MVP Exit)

- Ticker extraction precision > 95% on validation set
- Duplicate detection precision > 95% on labeled sample
- Thesis extraction judged “useful” on > 80% sample docs
- Obvious junk filtering > 85% precision
- Provenance available for all claim-bearing extracted fields
- Weekly digest adopted in real workflow for at least 4 consecutive weeks

---

## 16) Open Decisions to Finalize Before Build

1. Breadth-first vs depth-first corpus strategy
2. Public-only ingestion vs authenticated user-owned sources
3. Personalized ranking in MVP vs post-MVP
4. Full-text retention policy by source type
5. Minimum human review gate before “trusted corpus” status

---

## 17) Suggested Next Artifacts

1. SQL migration set for core schema
2. Pydantic models for extraction JSON contracts
3. Prompt templates + evaluation dataset
4. Queue topology and retry policy document
5. End-to-end sequence diagram for one document lifecycle
