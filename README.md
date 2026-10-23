# CloudPath API

FastAPI backend for the CloudPath unofficial AZ-900 study platform.

## Local development

Use Python 3.12. From this directory, create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.lock
$env:JWT_SECRET = (python -c "import secrets; print(secrets.token_hex(32))")
$env:AI_MODE = "demo"
uvicorn app.main:app --reload --port 8000
```

SQLite is used when `DATABASE_URL` is unset. For PostgreSQL, set `DATABASE_URL` to the database connection URL; the schema is initialized at startup.

## Render deployment

Create a PostgreSQL database and a Docker web service from this repository. Use the repository root as the Docker context and `./Dockerfile` as the Dockerfile. Set these service environment variables:

- `DATABASE_URL`: Render's internal database URL
- `JWT_SECRET`: a new random value of at least 32 characters
- `AI_MODE`: `demo` (or `live` when a provider key is configured)
- `CORS_ORIGINS`: the exact deployed Vercel origin, such as `https://your-app.vercel.app`
- `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`: only when using live AI

Set the Render health check path to `/health`. To run daily reminders, create a Render Cron Job from the same repository and database, using `python -m app.automation` as its command and a daily schedule.

Never commit `.env` files, database files, or production secrets.

## Diagnosing live AI failures

When `/buddy` or `/quizzes` returns the generic AI-service `502`, look in the
backend service's Render logs for `AI generation failed`. For example:

```text
AI generation failed: task=buddy error_class=HTTPStatusError upstream_status=401
```

This is an illustrative authentication failure, not a report of the current
deployment's status. The entry records the task, exception class and the provider
HTTP status for HTTP errors. Timeouts, response parsing errors and content
validation errors have `upstream_status=None` because no provider HTTP rejection
caused those failures.

After deploying the logging change, submit one Study Buddy question and inspect
the resulting diagnostic entry. API keys, prompts, uploaded excerpts, provider
response bodies and exception messages are deliberately excluded from this log.
The API continues to return the same generic error to learners. These diagnostics
help identify the cause; they do not themselves repair a failing provider call.
