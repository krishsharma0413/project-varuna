# Running varuna yourself

The technical guide: services, setup, everyday commands and how data is kept. For what varuna is,
see the [README](../README.md). Design references: [varuna-project-flow.md](varuna-project-flow.md)
(what and why) and [varuna-design.md](varuna-design.md) (how; see its "As built" section first).

## Services

Everything runs in Docker. Services talk to each other only through Redis, never by RPC or REST.

| Service | What it does |
|---|---|
| `web` | Caddy serving the React app and proxying `/api` to `api`. Site on http://localhost:8080 |
| `api` | FastAPI: public reads, Google sign-in, submissions, job status, disputes, rate limits |
| `worker` | Consumes the job stream: download → extract → transcribe/OCR → cleanup → claims → verify → store |
| `logger` | Moves log events from Redis into SQLite (`website_logs` and `business_critical` tables) |
| `searxng` | Free self-hosted metasearch, the first search provider. Internal only, no published port |
| `redis-queue` | Job stream, per-reel locks, rate limits, daily budget, log events. Never evicts; saved to disk |
| `redis-cache` | Read cache. 200 MB RAM, least-recently-used eviction, not saved |
| `mongo` | Optional local MongoDB (`--profile local-mongo`) for testing without Atlas |

MongoDB is Atlas (free tier). **No secondary indexes are created**: reels are keyed by their shortcode as
`_id` (Mongo's built-in index), everything else scans and is cached in Redis.

## Setup

1. **Config.** Copy `config.example.yaml` to `config.yaml` (gitignored, it holds secrets) and fill in:
   - `auth.google.client_id`: create an OAuth 2.0 *Web application* client in Google Cloud Console and
     add `http://localhost:8080` (and `http://localhost:5173` for frontend dev) under
     *Authorized JavaScript origins*. No client secret is needed.
   - `auth.jwt.secret`: a long random string (`python -c "import secrets;print(secrets.token_urlsafe(48))"`).
   - `auth.invited.mail`: the Google accounts allowed to submit reels.
   - `mongo.uri`: your Atlas connection string.
   - `openrouter.api_key`; optionally a paid search key (`search.serper.api_key`, `search.tavily.api_key` or
     `search.brave.api_key`, see [Web search](#web-search)) and `factcheck.google_api_key`.
   - `downloader.instaloader.username/password`: a **throwaway** Instagram account without 2FA.
2. **Run.** `docker compose up -d --build`, then open http://localhost:8080.

The models in `openrouter.models`, the pipeline settings and the prompts are shown publicly on
http://localhost:8080/transparency, generated live from `config.yaml` (secrets are never included).

`config.yaml` is read fresh on every access, so edits (invites, limits, TTLs, models, keys) apply
immediately with no restart. Only `mongo.uri` and `redis.*` need `docker compose restart api worker logger`.
If a save leaves the file invalid, the last valid version keeps being used and the error is logged.

The prompts live in `prompts.yaml` (repo root, next to `config.yaml`), also read fresh on every use and
validated the same way: each prompt only accepts its own `{placeholders}`. Every check stores the
prompts' `version` plus a hash of the file, so results stay traceable to the exact wording used.

## Restarting containers (menu)

```bash
./manage.sh                 # Linux / macOS (first time: chmod +x manage.sh)
manage.cmd                  # Windows, or double-click it
python3 scripts/manage.py   # anywhere with Python 3.8+
```

Shows every container's state, then lets you pick one or more (`2`, `2,3`, a name, or `A` for all)
and **restart**, **rebuild and restart** (after code changes) or **stop** them. Uses only the Python
standard library, and works with either `docker compose` or the older `docker-compose`. On Linux your
user needs to be in the `docker` group (or run it with `sudo`).

## Everyday commands

```bash
docker compose up -d --build                     # start / rebuild everything
docker compose logs -f worker                    # follow the pipeline
docker compose --profile local-mongo up -d       # also run a local MongoDB (set mongo.uri: mongodb://mongo:27017)

# read the logs database
#   website_logs(trace_id, timestamp, log_level, message)
#   business_critical(timestamp, trace_id, search_engine, event, detail): when a search engine starts failing / recovers
docker compose exec logger python -c "import sqlite3;db=sqlite3.connect('/data/logs/varuna_logs.sqlite');[print(r) for r in db.execute('select * from website_logs order by timestamp desc limit 20')]"
docker compose exec logger python -c "import sqlite3;db=sqlite3.connect('/data/logs/varuna_logs.sqlite');[print(r) for r in db.execute('select * from business_critical order by timestamp desc limit 20')]"

# tests and lint
docker build --target test -t varuna-test . && docker run --rm varuna-test
docker run --rm varuna-test ruff check --no-cache app tests main.py
```

Every API response carries an `X-Trace-Id` header. The same ID follows the request into the queued
job, so `select * from website_logs where trace_id = '…'` shows a submission's whole journey.

## Frontend development

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to the api container on 127.0.0.1:8000
npm run build        # typecheck + production build
```

React 19 + TypeScript + Vite, React Router, TanStack Query. The look is the "Poster" direction from
[docs/index.html](index.html): black and white, Archivo variable width, 3px borders, hard shadows.

## Private logs page

http://localhost:8080/admin/logs is only for the accounts listed in `auth.admins` (sign in with Google).
Everyone else, the page included, gets "not found". There are three ways to look:

- **Trace ID**, from a response's `X-Trace-Id` header or any log line: that request's whole journey, oldest first.
- **Reel link or ID**: every journey that touched the reel (from its jobs, plus any log line naming it).
- **Neither**: a time range, last 15 minutes to 30 days or a custom from/to. Newest first, with
  "Load older" and optional auto-refresh.

Level (debug/info/error), source (api/worker) and message-text filters apply to all three. The
**Business critical** tab lists search-engine failures and recoveries. The API reads the SQLite file
read-only through the shared `logs-data` volume.

## Topic gate

Before anything is downloaded, transcribed or searched, the worker reads the reel's caption (no video)
and asks the small model whether it's about one of the `topics` in `config.yaml`. Off-topic reels end
as `rejected`:
- They cost one short model call.
- They don't use up the daily budget.
- The decision is stored on the reel, so re-submitting it is free for `topic_gate.remember_hours`.
  Changing `topics` resets that.

Reels without a caption are rejected unless `topic_gate.empty_caption: allow`.

## Web search

Searches go through a fallback chain set in `search.providers` (`config.example.yaml`:
`serper → searxng → selenium`; `tavily` and `brave` are also available). Keyed providers without a key
are left out of the chain.

- **Serper** (2,500 free queries, then paid), only if `search.serper.api_key` is set.
- **SearXNG** (free, self-hosted container), asked one engine at a time in `search.searxng.engines`
  order: Google, then DuckDuckGo. Not Bing: through SearXNG it only searches the query's first word.
- **Selenium**: headless Chromium in the worker reading DuckDuckGo, Bing or Google results pages.

The first option that answers wins. One that fails (blocked, CAPTCHA, out of credits, down) is skipped
for `search.failure_cooldown_seconds`. The moment an engine **starts failing** and the moment it
**recovers** are written once each to the `business_critical` table, with the trace ID of the check
that noticed. Expect `searxng:google` and `selenium:google` to show up there: Google blocks automated
searches from most servers quickly. Email alerting on this table is future work.

## How data is kept

- One document per reel holds `current` (latest result) and `history[]`. When a result's TTL passes,
  the next request re-checks the reel: the old result moves into `history` and the new one takes its
  place. Nothing is deleted. TTLs per claim type, the history cap and whether raw transcript text is
  kept in history are all in `config.yaml` (`ttl`, `history`).
- Old finished jobs and request rows are deleted by the worker's housekeeping (`retention`).
- Media files are deleted as soon as a job finishes; only text and metadata are stored.
