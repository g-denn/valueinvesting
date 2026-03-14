# Idea Radar MVP Scaffold

This repository includes an executable MVP scaffold for **Idea Radar for Value Investing**.

If you want to start using it quickly, follow the **10-minute walkthrough** below.

## 0) Fastest way to run and see results

In one terminal:

```bash
./scripts/run_local.sh
```

In another terminal (after server starts):

```bash
./scripts/bootstrap_and_demo.sh
```

That second script will:
1. bootstrap your Substack list
2. bootstrap reference sources (DataRoma)
3. ingest a sample note
4. print feed/search/digest JSON so you can immediately see output

---

## 1) What this app does right now

- Register Substack sources in bulk via curated list or custom URLs.
- Register reference sites (including DataRoma) as tracked sources.
- Ingest investment writeups via:
  - `POST /documents/paste`
  - `POST /documents/url`
  - `POST /documents/upload`
- Add Substack input points:
  - `POST /sources/substack`
  - `POST /sources/substack/bootstrap`
  - `POST /sources/reference/bootstrap`
- Process each document through a basic MVP pipeline:
  - ingest -> clean -> extract thesis card (heuristic) -> score -> dedup -> index
- Browse and query outputs:
  - `GET /feed`
  - `GET /search?q=...`
  - `GET /ideas/{id}`
  - `GET /digests/weekly/latest`
- Add human feedback:
  - `PATCH /ideas/{id}`
  - `POST /ideas/{id}/tags`

---

## 2) Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Then run the API:

```bash
uvicorn app.main:app --reload
```

API docs will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 3) 10-minute walkthrough (copy/paste)


### Optional: Bootstrap your Substack source list (your provided list)

This project now ships with a preloaded list at `data/substack_sources.txt`.

To register all of them into the DB in one shot:

```bash
curl -X POST 'http://127.0.0.1:8000/sources/substack/bootstrap' \
  -H 'Content-Type: application/json' \
  -d '{"use_default_file": true}'
```

You can also pass additional URLs inline:

```bash
curl -X POST 'http://127.0.0.1:8000/sources/substack/bootstrap' \
  -H 'Content-Type: application/json' \
  -d '{
    "use_default_file": true,
    "urls": [
      "https://example.substack.com/",
      "https://substack.com/@examplehandle"
    ]
  }'
```

The API normalizes Substack URLs and computes RSS feed URLs automatically (`.../feed`).

### Optional: Bootstrap reference sources (DataRoma included)

This project now ships with `data/reference_sources.txt`, seeded with:
- `https://www.dataroma.com/m/home.php`

Register it into the DB:

```bash
curl -X POST 'http://127.0.0.1:8000/sources/reference/bootstrap' \
  -H 'Content-Type: application/json' \
  -d '{"use_default_file": true}'
```

You can append extra reference sites via the `urls` field in the same payload.


### Step A: Ingest text manually

```bash
curl -X POST 'http://127.0.0.1:8000/documents/paste' \
  -H 'Content-Type: application/json' \
  -d '{
    "source_name": "manual",
    "title": "Acme Corp",
    "text": "Long ACME because recurring revenue is underappreciated. Catalyst: product launch. Risk: execution misses. Valuation at 8x EV/EBIT looks discounted."
  }'
```

Expected result:
- A `Document` JSON response with fields like:
  - `id`
  - `status` (should become `INDEXED`)
  - `quality_score`

### Step B: View ranked feed

```bash
curl 'http://127.0.0.1:8000/feed'
```

This returns the highest-quality documents first.

### Step C: Search

```bash
curl 'http://127.0.0.1:8000/search?q=ACME'
```

This searches title/raw/clean text.

### Step D: Open extracted idea

```bash
curl 'http://127.0.0.1:8000/ideas/1'
```

This returns extracted thesis fields (`one_line_thesis`, `catalysts`, `risks`, etc.).

### Step E: Add a tag

```bash
curl -X POST 'http://127.0.0.1:8000/ideas/1/tags' \
  -H 'Content-Type: application/json' \
  -d '{"tag":"gold","note":"high signal"}'
```

### Step F: Get weekly digest

```bash
curl 'http://127.0.0.1:8000/digests/weekly/latest'
```

---

## 4) How the pipeline works internally

When you ingest a document, `app/services/pipeline.py` currently does:

1. Get/create source
2. Store raw + clean text in `documents`
3. Fingerprint text for dedup (`sha256` on canonicalized text)
4. Detect direction (`long`/`short`/`watchlist`)
5. Extract a heuristic idea card (thesis, bullets, catalysts, risks, valuation)
6. Compute heuristic quality score
7. Create `ideas` record and mark document `INDEXED`

---

## 5) Data model at a glance

Main tables currently used:
- `sources`
- `documents`
- `companies`
- `ideas`
- `user_tags`

Database default:
- SQLite file `idea_radar.db` in repo root (unless `DATABASE_URL` is set).

---

## 6) Running tests

```bash
pytest -q
```

The tests in `tests/test_api.py` cover:
- paste ingestion
- feed/search
- idea retrieval
- tagging
- weekly digest endpoint

---

## 7) Known MVP limitations (important)

- Extraction is deterministic + heuristic, not LLM-backed yet.
- Search is SQL text matching, not semantic vector search yet.
- No async queue workers yet (pipeline runs inline on request).
- No provenance spans/model audit records yet.

This is intentionally a scaffold so you can iterate quickly.

---

## 8) Suggested next upgrades

1. Add Alembic migrations.
2. Add async job queue for ingestion/extraction.
3. Replace heuristic extraction with schema-validated LLM extraction.
4. Add chunking + evidence span provenance.
5. Add embeddings + hybrid semantic search.
