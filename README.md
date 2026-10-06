# Job board

A private dashboard of new Bay Area roles, scored against my resume.

- `poller/`: Python scan of ~728 public career boards. Runs on GitHub Actions every 30 minutes (Greenhouse, Ashby, Lever) and hourly (Workday and the rest). Writes Bay Area hybrid/onsite and US-remote roles into Postgres. Nothing is cut; every role gets a score.
- `web/`: Next.js app on Vercel. A grid of cards, a day filter (default: since 5pm Pacific yesterday), Bay Area vs Remote filter, applied/contacted marks stored in Postgres.

## Scoring (0-100)
| Part | Max | How |
|---|---|---|
| Role fit | 25 | title terms (AI engineer, full stack, forward deployed, ...) from `poller/profile.json`; non-engineering titles get 0 |
| Skills | 25 | resume keywords found in the posting body |
| Experience | 30 | largest "N+ years" in a requirement (not "preferred"), or seniority implied by the title; 0-2 yrs = 30, 3 = 24, 4 = 16, 5 = 8, 6 = 3, 7+ = 0; intern/new-grad titles are capped |
| Location | 20 | San Francisco 20, other Bay Area 12, remote 0 |

The profile (resume keywords and years) is NOT in the repo. Locally it is `poller/profile.json` (gitignored); in CI it is the `PROFILE_JSON` secret. Without either, `profile.example.json` is used.

## Days and dates
A role's day is the employer's own posting date when the feed has one (Greenhouse `first_published`, Ashby `publishedAt`, Lever `createdAt`, Workday "Posted N days ago"), otherwise the time the poller first saw it. Roles already open when a board is first scanned and with no employer date are marked baseline and have no day, so they never show up as new.

## Setup
1. Postgres (Neon via the Vercel Marketplace). Put its URL in `DATABASE_URL`.
2. Vercel project with root directory `web/` and env vars `DATABASE_URL`, `SITE_PASSWORD`, `AUTH_SECRET` (`openssl rand -hex 32`).
3. GitHub repo secrets: `DATABASE_URL`, `PROFILE_JSON` (contents of `poller/profile.json`).
4. Run the `poll` workflow once by hand (tier `all`), then the schedules take over.

GitHub disables scheduled workflows on a public repo after 60 days without repo activity; re-enable from the Actions tab if that happens.

## Local development
    python3 -m venv .venv && .venv/bin/pip install -r poller/requirements.txt
    DATABASE_URL=... .venv/bin/python poller/poll.py --tier fast --only "Stripe,Mintlify"
    cd web && npm install && npm run dev      # http://localhost:3100

## Application Helper
Each card's "Open application" link goes straight to the ATS apply page (Greenhouse `job-boards.greenhouse.io`, Ashby `/application`, Lever `/apply`), which are the hosts the extension runs on. "Export for Application Helper" downloads a `daily-refresh-YYYY-MM-DD.json` in the extension's import format: the top 40 not-yet-applied roles in the current view, plus your applied URLs and companies so they are excluded.
