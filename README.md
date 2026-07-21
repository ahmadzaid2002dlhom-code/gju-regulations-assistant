# GJU Student Regulations Assistant

This repository contains Phase 1 of a page- and article-aware RAG assistant for
official GJU regulations. It runs Streamlit and PDF extraction locally while
OpenAI provides embeddings and answer generation, and Supabase stores metadata,
searchable text, and 768-dimensional vectors.

## What is implemented

- Checksum-based PDF ingestion and version tracking
- Page-level PyMuPDF extraction with printed-page heuristics
- English and Arabic article and heading detection
- Article-preserving chunks with token overlap only for long articles
- OpenAI `text-embedding-3-small` embeddings at 768 dimensions
- Supabase vector, full-text, and section-title search
- Weighted hybrid reranking and evidence diversification
- OpenAI Responses API answers restricted to retrieved evidence
- Streamlit source cards, official links, and evidence inspection
- Row-level security that gives the public app read-only access to current data
- Unit tests for chunking, retrieval merging, languages, and citations

## 1. Create the local environment

The existing `.env` is ignored by Git and already contains `OPENAI_API_KEY`.
Do not replace or commit it. Add the Supabase values to that same file:

```text
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
```

The public Streamlit app uses only the anonymous key. The service-role key is
loaded only by scripts under `scripts/`.

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Create the Supabase database

Open the Supabase SQL editor and run these files in order:

1. `database/schema.sql`
2. `database/functions.sql`
3. `database/indexes.sql`

The SQL enables `pgvector`, creates the four core tables, enables RLS, and adds
three read-only RPC search functions. Keep `EMBEDDING_DIMENSIONS=768`; changing
it requires changing the SQL vector type and regenerating all embeddings.

## 3. Configure official documents

Copy real official PDF URLs into `data/sources.json`. Use
`data/sources.example.json` as the shape, but do not ingest its placeholder URL.

```json
[
  {
    "title": "Official document title",
    "url": "https://www.gju.edu.jo/official-file.pdf",
    "department": "Responsible GJU department",
    "language": "en",
    "document_type": "regulation",
    "academic_year": "2026",
    "status": "current"
  }
]
```

Use `language: "ar"` for Arabic documents and `document_type: "german_year"`
for German Year material.

## 4. Apply the first ingestion

```powershell
python scripts/ingest_documents.py
```

Unchanged checksums are skipped. Reindex one unchanged document only when
necessary:

```powershell
python scripts/reindex_document.py "Exact document title" --confirm
```

Reindexing builds a new hidden version first. Only after all pages, sections,
chunks, and vectors succeed does it mark the older version superseded. Normal
content updates use the same safe version-swap flow.

## 5. Run the application

```powershell
streamlit run app.py
```

Open `http://localhost:8501`. Until Supabase is configured, the interface opens
in setup mode and does not make API calls.

To test from the terminal after ingestion:

```powershell
python scripts/test_question.py "Can I register extra credit hours in my final semester?"
```

## 6. Verify locally

```powershell
python -m pytest -q
```

The unit tests do not call OpenAI or Supabase. Add verified real questions to
`tests/evaluation_questions.json` after the first official PDFs are indexed.

## Security boundaries

- `.env`, raw PDFs, processed snapshots, and virtual environments are ignored.
- `.dockerignore` also excludes secrets and local data from image build contexts.
- The browser never receives the OpenAI or service-role key.
- Students cannot trigger ingestion, deletion, or reindexing.
- Public database access is restricted by RLS to current document rows.
- Questions, retrieval candidates, evidence chunks, and output tokens are capped.
- `delete_document.py` requires the document UUID twice before deletion.

## Deployment path

The included Dockerfile runs the same app on Render, Railway, or another
container platform. Add only `OPENAI_API_KEY`, `SUPABASE_URL`, and
`SUPABASE_ANON_KEY` to the public service. Keep ingestion and
`SUPABASE_SERVICE_ROLE_KEY` in a separate administrative job.

GitHub Actions runs the unit suite on pushes and pull requests. The separate
`Ingest GJU documents` workflow is manual by default; add a schedule only after
the source manifest and repository secrets have been verified.
