# CNews Compiler

Automated news research and weekly newsletter publishing.

The daily Render cron researches a rotating topic, emails the summary, and stores the exact sent email in Supabase. The weekly Render cron reads recent stored entries, synthesizes trends and highlights with OpenAI, optionally emails the digest, and posts it to LinkedIn.

## What It Does

- Runs daily topic research with the configured LLM provider.
- Sends daily summaries through Gmail.
- Stores daily output in PostgreSQL/Supabase table `news_compiler_db`.
- Compiles a weekly digest from the last N calendar days.
- Posts the weekly digest to LinkedIn.
- Supports local Streamlit testing.

## Database

The app creates this table automatically on first insert:

```text
news_compiler_db
  datetime  DateTime primary key
  topic     String(300)
  content   Text
```

Use a Supabase PostgreSQL connection string as `DATABASE_URL`.

## Environment Variables

Copy `.env.example` to `.env` for local use. In Render, set these per cron service.

Required for daily research:

```bash
DATABASE_URL=postgresql://...
LLM_PROVIDER=openai
GMAIL_EMAIL=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
RECIPIENT_EMAILS=person1@example.com person2@example.com
```

Optional for daily research:

```bash
RESEARCH_TOPIC=
```

If `RESEARCH_TOPIC` is blank, `orchestrator.py` uses the weekday topic rotation.

LLM provider options:

```bash
# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_TOPIC_MODEL=gpt-5
OPENAI_NEWSLETTER_MODEL=gpt-4o-mini

# Azure OpenAI
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=your-default-deployment
AZURE_OPENAI_TOPIC_DEPLOYMENT=
AZURE_OPENAI_NEWSLETTER_DEPLOYMENT=
```

For Azure OpenAI, `AZURE_OPENAI_DEPLOYMENT` is used as the fallback deployment for both flows. The topic/newsletter-specific deployment variables are optional.

Required for weekly digest:

```bash
DATABASE_URL=postgresql://...
LLM_PROVIDER=openai
WEEKLY_DIGEST_DAYS=7
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_AUTHOR_URN=urn:li:person:your-member-id
```

Optional for weekly digest:

```bash
OPENAI_NEWSLETTER_MODEL=gpt-4o-mini
RECIPIENT_EMAILS=person1@example.com person2@example.com
LINKEDIN_API_VERSION=202506
```

## Render Cron Jobs

This repo includes `render.yaml` with two cron jobs:

```bash
python orchestrator.py
python weekly_digest.py
```

The weekly job reads `WEEKLY_DIGEST_DAYS` from the environment, so the Render command does not need shell interpolation.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Then edit `.env`.

## Local Commands

Run daily research:

```bash
python orchestrator.py
```

Run daily research with explicit topic and recipients:

```bash
python orchestrator.py "AI product launches this week" recipient@example.com
```

Initialize the DB table:

```bash
python orchestrator.py --init-db
```

Preview weekly digest without LinkedIn posting:

```bash
python weekly_digest.py --dry-run
```

Compile weekly digest but skip LinkedIn:

```bash
python weekly_digest.py --no-post
```

Run the Streamlit app:

```bash
streamlit run app.py
```

## LinkedIn Token Setup

Paste a valid token into `LINKEDIN_ACCESS_TOKEN` and set `LINKEDIN_AUTHOR_URN`.

## Project Layout

```text
orchestrator.py              Daily research, email, DB insert
weekly_digest.py             Weekly DB lookup, digest generation, LinkedIn posting
topic_research.py            Configured LLM research call
newsletter_compiler.py       Configured LLM newsletter synthesis
database.py                  SQLAlchemy storage layer
send_email.py                Gmail delivery
linkedin_connector.py        LinkedIn posting client
skills/                      Prompt skills used by research and digest flows
schemas/                     Structured output schemas
render.yaml                  Render cron configuration
```
