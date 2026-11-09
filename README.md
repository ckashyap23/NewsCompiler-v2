# CNews Compiler

Daily AI news research delivered to email and WhatsApp, plus a weekly digest published to LinkedIn. Deploy the two workflows as independent Railway cron services from this repository. An optional HTTP API uses the same workflows for manual triggers.

## Project structure

```text
daily/
  orchestrator.py          Daily research, archive, and channel delivery
  topic_research.py        Sourced news research
  whatsapp_connector.py    WhatsApp relay client
  railway.json             Daily cron deployment configuration
weekly/
  digest.py                Weekly compilation and publishing
  newsletter_compiler.py   Structured newsletter generation
  linkedin_connector.py    LinkedIn feed posting
  railway.json             Weekly cron deployment configuration
shared/
  database.py              PostgreSQL/Supabase storage
  llm_provider.py          OpenAI and Azure OpenAI provider selection
  send_email.py            Gmail SMTP delivery
  paths.py                 Repository resource and .env paths
api.py                     Optional FastAPI endpoints
deploy/railway-api.json    Optional HTTP service configuration
skills/                    Research and newsletter prompt instructions
schemas/                   Weekly newsletter JSON schema
tests/                     Checks with mocked external services
requirements.txt           Runtime dependencies for all services
requirements-dev.txt       Runtime dependencies plus the test HTTP client
.env.example               Configuration template; never commit .env
```

Run Python modules from the repository root with `python -m ...`. Both packages use the shared database and LLM utilities. The root `.env`, skill prompts, and output schema are resolved relative to the repository, not the individual package folders.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Copy the template only when creating a new `.env`; preserve an existing configured file. Fill in the provider, database, recipients, and channel credentials you need.

```bash
python -m daily.orchestrator --help
python -m weekly.digest --help
python -m unittest discover -s tests -v
```

The tests mock research and external delivery. They do not send messages or publish LinkedIn posts.

## Railway: two scheduled jobs

The supplied configs use these default schedules:

| Service | Railway Config File | Start command | UTC cron | India time |
| --- | --- | --- | --- | --- |
| `news-daily` | `/daily/railway.json` | `python -m daily.orchestrator` | `0 9 * * *` | Every day, 2:30 PM IST |
| `news-weekly` | `/weekly/railway.json` | `python -m weekly.digest --no-email` | `0 10 * * 0` | Sunday, 3:30 PM IST |

These are editable defaults. Railway cron uses UTC. The weekly job starts one hour after Sunday's daily job; this is a time gap, not a dependency or guarantee that the daily job succeeded. Railway may vary execution times by a few minutes. See [Railway cron documentation](https://docs.railway.com/cron-jobs).

### 1. Push the code

Commit the intended project changes and push them to `master` in `ckashyap23/NewsCompiler-v2`. Railway deploys the GitHub version, not this local folder. Keep `.env` untracked.

### 2. Create the daily service

1. Create a Railway project, then add an empty service named `news-daily` so you can configure it before its first deployment.
2. Connect `ckashyap23/NewsCompiler-v2` as its GitHub source and select branch `master`. Keep the Root Directory at the repository root (`/` or unset). Do not set it to `/daily`, because shared code, prompts, requirements, and schemas live outside that folder.
3. Set **Railway Config File** to `/daily/railway.json` in service settings. It supplies the build command (`pip install -r requirements.txt`), start command, daily schedule, and `NEVER` restart policy. Clear old HTTP health-check settings if reusing an existing service. No domain or port is required.
4. Add the daily variables below in the Variables tab before applying the deployment.
5. Apply/deploy the service. Confirm the effective command and cron schedule match the table.

Both services share a repository root and have different config files, following [Railway's shared monorepo model](https://docs.railway.com/deployments/monorepo).

Daily variables for OpenAI with email and WhatsApp:

```dotenv
DATABASE_URL=postgresql://...
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_TOPIC_MODEL=gpt-5
RESEARCH_TOPIC=
RECIPIENT_EMAILS=reader1@example.com reader2@example.com
GMAIL_EMAIL=your-sender@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password
API_PATH=https://whatsappserver-production-2b41.up.railway.app
API_POST_PATH=/api/messages/send
BEARER_TOKEN=your-whatsapp-relay-token
RECEIPENT_PHONE_NUMBERS=918340412106 919876543210
PYTHONUNBUFFERED=1
```

Blank `RESEARCH_TOPIC` enables the UTC weekday topic rotation. Recipients are whitespace-separated. Keep the exact spelling `RECEIPENT_PHONE_NUMBERS`. A channel is skipped when its recipient variable is empty; at least one channel needs recipients.

Gmail delivery uses SMTP. **Railway requires Pro or above for SMTP**; Free, Trial, and Hobby block it. For WhatsApp-only operation, leave `RECIPIENT_EMAILS` empty. Supporting email on those plans would require a separate change to an HTTPS email provider. After upgrading a Railway plan for SMTP, redeploy the service. See [Railway outbound networking](https://docs.railway.com/networking/outbound-networking).

The relay receives `Authorization: Bearer <BEARER_TOKEN>` and this JSON at `API_PATH` + `API_POST_PATH`:

```json
{
  "recipients": ["918340412106", "919876543210"],
  "message": "The exact generated daily text also used as the email body"
}
```

A relay HTTP 2xx confirms relay acceptance, not delivery to a device. Requests use HTTPS, timeouts, and no automatic POST retries.

### 3. Create the weekly service

1. Add a second empty service in the same project named `news-weekly`.
2. Connect the same repository and `master` branch, again leaving Root Directory at `/` or unset.
3. Set **Railway Config File** to `/weekly/railway.json`. It configures `python -m weekly.digest --no-email`, the Sunday schedule, and `NEVER` restart policy. No HTTP health check, domain, or port is needed.
4. Set the following variables, using the **same database** as the daily job:

```dotenv
DATABASE_URL=postgresql://...
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_NEWSLETTER_MODEL=gpt-4o-mini
WEEKLY_DIGEST_DAYS=7
LINKEDIN_ACCESS_TOKEN=your-valid-access-token
LINKEDIN_AUTHOR_URN=urn:li:person:your-member-id
LINKEDIN_API_VERSION=202610
PYTHONUNBUFFERED=1
```

5. Apply/deploy and confirm the weekly command and cron schedule. The supplied command publishes to LinkedIn and disables weekly email, even if shared settings contain email recipients.

The LinkedIn token needs permission to post as the author (for a personal profile, `w_member_social`). Keep the token valid and the API version supported. Automatic OAuth refresh is not implemented. Publishing creates a regular LinkedIn feed post rather than a LinkedIn Newsletter edition.

### 4. Verify the first runs

1. Trigger one daily execution when ready to send real messages. Check logs, the email/WhatsApp recipients, and a new row in `news_compiler_db`.
2. Once daily data exists, trigger one weekly execution when ready for a real LinkedIn post. Check logs and the profile feed.
3. Confirm each process finishes and exits. Railway skips a scheduled execution if the previous one is still running.
4. Review failures before manually rerunning. A failed or timed-out delivery may have succeeded for some recipients. Each run generates new content; there is no persistent idempotency key or automatic channel-specific recovery. Restart policy `NEVER` avoids automatic restarts after partial delivery.

For a weekly preview without publishing or email, run locally with the configured database:

```bash
python -m weekly.digest --dry-run
```

The seven-calendar-day query includes the current UTC day and the previous six UTC days. Sunday's 3:30 PM IST run normally covers Monday through Sunday if the daily runs succeed. The first week can contain fewer entries. If there are no entries, the weekly CLI logs that and exits with code 1.

To change timing, edit `deploy.cronSchedule` in the corresponding Railway JSON and redeploy. Config-file values take precedence over dashboard values; see [Railway configuration reference](https://docs.railway.com/config-as-code/reference).

## Database

Use the same PostgreSQL/Supabase `DATABASE_URL` in both services. Use a connection URL reachable from Railway. The daily job creates the table on its first insert:

```text
news_compiler_db
  datetime  DateTime primary key
  topic     String(300)
  content   Text
```

Daily content is stored before delivery. It remains available to weekly compilation even if email or WhatsApp delivery fails. A database error stops delivery.

## Azure OpenAI alternative

Both workflows also support `LLM_PROVIDER=azure_openai`. Instead of OpenAI credentials, configure:

```dotenv
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_API_VERSION=your-supported-api-version
AZURE_OPENAI_DEPLOYMENT=your-default-deployment
AZURE_OPENAI_TOPIC_DEPLOYMENT=
AZURE_OPENAI_NEWSLETTER_DEPLOYMENT=
```

Operation-specific deployment settings override the fallback. The daily deployment must support the Responses API web-search request used by `daily/topic_research.py`; verify support for your Azure deployment before production use.

## Other local commands

```bash
python -m daily.orchestrator --init-db
python -m daily.orchestrator "AI product launches this week" reader@example.com
python -m weekly.digest --days 14 --no-email
python -m weekly.digest --no-post --no-email
```

Normal commands send real messages or publish posts unless the skip/preview flags are used. `--no-post` can fall back to a local preview if compilation fails. `--dry-run` skips both posting and email.

## Optional HTTP API

The API is retained for manual HTTP triggers and shares the package workflows. It is not required for the two cron services. To deploy it as an additional always-running service, keep the repository root and select `/deploy/railway-api.json`. Add the relevant workflow credentials plus a long random `BACKEND_API_TOKEN`, and generate a public domain.

Start locally:

```bash
python -m uvicorn api:app --reload --port 8000
```

| Endpoint | Behavior | Optional JSON body |
| --- | --- | --- |
| `POST /daily-news` | Research, archive, send email and/or WhatsApp | `{"topic":"AI updates","email":true,"whatsapp":true}` |
| `POST /weekly-digest` | Compile and publish to LinkedIn without email | `{"days":7}` |
| `GET /health` | Public process health check | None |

Both POST routes accept an empty body and require `Authorization: Bearer <BACKEND_API_TOKEN>`. The backend token is separate from the WhatsApp relay's `BEARER_TOKEN`. Cron services do not require `BACKEND_API_TOKEN`. API documentation is at `/docs`.

HTTP requests run synchronously. A caller timeout does not cancel work already running. Daily HTTP 502 responses report per-channel partial results; `sent` means SMTP acceptance and `accepted` means relay acceptance. LinkedIn failure returns HTTP 502. With no stored entries, the weekly API returns `status: skipped`. The health check verifies process responsiveness, not external credentials.

The API does not schedule itself. Avoid scheduling an API call for a workflow already scheduled by its cron service, which would send duplicate editions.
