# univr-fellowships-crawler

A Python crawler that monitors the [UNIVR Research Fellowship listings](https://www.univr.it/it/concorsi/borse-di-studio-di-ricerca) and sends a **Telegram notification** whenever a new post appears.  
Previously seen fellowships are stored in **Supabase** to avoid duplicate notifications.

## Features

- Scrapes all pages of the UNIVR fellowship listing
- **Early-stop**: stops crawling as soon as an entire page contains only already-known entries
- Sends rich Telegram notifications (title, deadline, department, link)
- Configurable polling interval or one-shot execution (for external schedulers / cron)
- Docker-first: single `docker compose up -d` to deploy

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Docker + Docker Compose | any recent |
| Supabase project | free tier is fine |
| Telegram Bot | created via [@BotFather](https://t.me/BotFather) |

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

### 2. Configure environment variables

```bash
cp .env.example .env
# then edit .env with your values
```

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | `anon` or `service_role` key |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat / channel ID |
| `POLL_INTERVAL_SECONDS` | Seconds between crawls (default `3600`). Set to `0` to run once and exit. |

### 3a. Run with Docker (recommended)

```bash
docker compose up -d
```

Logs:

```bash
docker compose logs -f
```

### 3b. Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python crawler.py
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
6. After finishing, sleep for `POLL_INTERVAL_SECONDS` and start again.

---

## Project structure

```
.
├── crawler.py           # Main crawler script
├── requirements.txt     # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── schema.sql           # Supabase table definition
├── .env.example         # Template for environment variables
└── README.md
```
