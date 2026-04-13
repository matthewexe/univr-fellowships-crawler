# univr-fellowships-crawler

A Python crawler that monitors the [UNIVR Research Fellowship listings](https://www.univr.it/it/concorsi/borse-di-studio-di-ricerca) and sends a **Telegram notification** whenever a new post appears.  
Previously seen fellowships are stored in **Supabase** to avoid duplicate notifications.

## Features

- Scrapes all pages of the UNIVR fellowship listing
- **Early-stop**: stops crawling as soon as an entire page contains only already-known entries
- Sends rich Telegram notifications (title, deadline, department, link)
- Runs once a day at **08:00 UTC** via a GitHub Actions scheduled workflow
- Docker image available for local / self-hosted runs

---

## Prerequisites

| Tool | Version |
|------|---------|
| Supabase project | free tier is fine |
| Telegram Bot | created via [@BotFather](https://t.me/BotFather) |
| GitHub repository | to host the Actions workflow |

---

## Quick start

### 1. Create the Supabase table

Open the **SQL Editor** in your Supabase project and run:

```sql
-- contents of schema.sql
CREATE TABLE IF NOT EXISTS fellowships (
    id          TEXT        PRIMARY KEY,
    title       TEXT        NOT NULL,
    url         TEXT        NOT NULL,
    date        TEXT,
    deadline    TEXT,
    department  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2. Add GitHub Actions secrets

Go to **Settings → Secrets and variables → Actions** in your repository and add:

| Secret | Description |
|--------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | `anon` or `service_role` key |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat / channel ID |

### 3. Deploy

Push the repository to GitHub. The workflow at `.github/workflows/crawler.yml` will run automatically every day at **08:00 UTC**.

To trigger a run manually:

```
GitHub → Actions → UNIVR Fellowship Crawler → Run workflow
```

### Run locally (optional)

```bash
cp .env.example .env
# edit .env with your values
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python crawler.py
```

Or with Docker:

```bash
cp .env.example .env
docker compose up
```

---

## How it works

1. Fetch the first page of the fellowship listing.
2. Detect the page size from pagination links.
3. For each fellowship on the page:
   - If **not** in the database → insert it and send a Telegram notification.
   - If already in the database → skip.
4. **Early stop**: if **every** entry on a page is already known, stop pagination.
5. Otherwise fetch the next page and repeat.
6. GitHub Actions runs the crawler once a day at **08:00 UTC** via a `schedule` trigger.

---

## Project structure

```
.
├── .github/workflows/
│   └── crawler.yml      # GitHub Actions scheduled workflow
├── crawler.py           # Main crawler script
├── requirements.txt     # Python dependencies
├── Dockerfile           # For local / self-hosted runs
├── docker-compose.yml
├── schema.sql           # Supabase table definition
├── .env.example         # Template for environment variables (local use)
└── README.md
```
