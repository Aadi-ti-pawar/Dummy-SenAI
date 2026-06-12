# Backend

This backend starts with the ingestion milestone from the SenAI technical assessment.
It follows the existing `database_schema.sql` as the database contract and keeps
ingestion-specific metadata in existing JSONB columns instead of creating parallel
tables.

## Current scope

- `POST /api/ingest` accepts one email payload.
- The payload is validated, normalized, deduplicated by `message_id`, linked to a
  contact and thread, scored with fast heuristics, stored in PostgreSQL, and tracked
  with a `processing_jobs` row.
- `GET /api/status/{job_id}` returns processing job state.
- `GET /health` checks that the API process is alive.
- `GET /api/health` checks application and database availability.
- `scripts/simulate_stream.py` replays `email-data-advanced.json` into the API at a
  configurable speed.
- Full phase documentation: [`docs/phase-01-ingestion-pipeline.md`](docs/phase-01-ingestion-pipeline.md).

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Create the database and apply the existing SQL schema:

```bash
psql -U postgres -d crm_ai -f database_schema.sql
```

If `psql` is not available, use the Python helper after configuring `.env`:

```bash
python scripts/apply_schema.py
```

Or start PostgreSQL and Redis with Docker Compose from the repository root:

```bash
docker compose up -d postgres redis
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Run the worker when Redis is available:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

Replay the dataset:

```bash
python ..\scripts\simulate_stream.py --speed 1
python ..\scripts\simulate_stream.py --speed 10 --limit 20
```

## Ingestion contract

Required fields:

- `message_id`
- `sender`
- `subject`
- `body`
- `timestamp`
- `thread_id`

`subject` and `body` may be empty strings. Missing fields, malformed timestamps,
invalid email addresses, oversized payloads, and malformed JSON return the standard
error envelope:

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid request payload",
  "details": {}
}
```

## Design notes

- Idempotency uses the existing unique constraint on `emails.message_id`.
- Initial triage maps to existing columns: `emails.category`, `emails.urgency`,
  `emails.requires_human`, flag columns, and `threads.priority`.
- Numeric priority score, reasons, normalization warnings, and basic entity hints are
  stored in `emails.raw_entities.ingestion`.
- The API commits ingestion before attempting Celery dispatch. If Redis is down, the
  job stays in `Pending` with dispatch metadata so the email is not lost.
