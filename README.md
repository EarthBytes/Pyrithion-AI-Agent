# Multi-Agent Research & Automation System

A small multi-agent system that takes an analytics request, researches the data, writes a report, and emails the result.

The system is split into a few simple agents:

| Agent        | What it does                           |
| ------------ | -------------------------------------- |
| **Planner**  | Breaks the request into steps          |
| **Data**     | Generates and runs read-only SQL       |
| **ML**       | Looks for anomalies and trends         |
| **Research** | Finds relevant information from Qdrant |
| **Writer**   | Writes the final report                |
| **Executor** | Sends the report by email              |

Tasks run in the background. You create a task and then check its status using the task ID.

## Quick start

### 1. Set up the environment

```bash
cp .env.example .env
```

Add the required values to `.env`, including:

* `POSTGRES_PASSWORD`
* `LLM_API_KEY`
* `SMTP_*`
* `API_KEY` (optional for local development)

### 2. Run with Docker

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build
```

Then open:

* App: http://localhost:8000
* API docs: http://localhost:8000/docs

### 3. Run the app locally

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start Postgres and Qdrant, then initialise the database:

```bash
python scripts/init_db.py
python scripts/load_docs.py
uvicorn app.main:app --reload
```

## API

If `API_KEY` is set, API requests need an `X-API-Key` header.

### Create a task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"goal":"Analyse energy usage anomalies and email a report","email":"you@example.com"}'
```

You will get a task ID back:

```json
{
  "task_id": "...",
  "status": "pending"
}
```

### Check the result

Use the task ID to check the task:

```bash
curl http://localhost:8000/api/result/<task_id> \
  -H "X-API-Key: your-key"
```

Keep polling until the status is either `completed` or `failed`.

### Health checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Configuration

The main environment variables are:

| Variable                      | What it does                                |
| ----------------------------- | ------------------------------------------- |
| `DATABASE_URL` / `POSTGRES_*` | Postgres connection                         |
| `QDRANT_URL`                  | Qdrant connection                           |
| `LLM_PROVIDER`                | LLM provider                                |
| `LLM_API_KEY`                 | LLM API key                                 |
| `LLM_MODEL`                   | LLM model to use                            |
| `SMTP_*`                      | Email settings                              |
| `API_KEY`                     | Protects the API                            |
| `SQL_ALLOWED_TABLES`          | Tables the SQL agent can access             |
| `SQL_ROW_LIMIT`               | Maximum number of SQL rows returned         |
| `EMBEDDING_PROVIDER`          | Embedding provider                          |
| `EMBEDDING_MODEL`             | Embedding model when using the API provider |

See `.env.example` for the full list.

## Security

A few basic safeguards are built in:

* SQL is read-only (`SELECT` only).
* SQL can only access allowlisted tables.
* Only one SQL statement is allowed at a time.
* SQL results have a row limit.
* The API can be protected with `API_KEY`.
* Secrets are stored in `.env`, which should not be committed to Git.

If the API is exposed outside local development, set a strong `API_KEY`.

## Tests

Run the test suite with:

```bash
pytest
```

## CI

GitHub Actions runs the tests and builds the Docker image on pushes and pull requests to `main`.
