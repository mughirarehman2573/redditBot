# Reddit Niche-Swappable Warm-Up MVP (Do-It-Now Build)

**What you get right now**
- FastAPI backend + SQLite DB
- Email summaries of *planned* comments (optional; SMTP envs)
- Minimal dashboard to review planned comments and approve to post
- Niche packs via YAML (start with golf)
- Scheduler-friendly endpoints (you can call `/plan-run` from cron for now)

## Quickstart

1. Python 3.10+ recommended. Install deps:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` → `.env` and fill values. **Rotate any keys that were ever shared.**

3. Get a Reddit refresh token for each account (one-time). Example helper is not included; you can use PRAW's script-app flow.
   Save refresh tokens via the UI or POST `/accounts`.

4. Run the app:
   ```bash
   uvicorn main:app --reload
   ```

5. Open http://127.0.0.1:8000/ — you'll see a minimal dashboard:
   - Add accounts (id/secret/refresh token are used under the hood)
   - Pick/confirm niche per account
   - Click **Plan** to queue 1-3 short replies per account
   - Approve to **Post**

6. Optional: trigger planning from cron (every 20–40 mins with jitter):
   ```bash
   curl -X POST http://127.0.0.1:8000/plan-run -H "Content-Type: application/json" -d '{"account_id": 1}'
   ```

## Notes
- This build forbids links in generated comments and strips anything that looks promotional.
- It keeps comments **short and specific** to reduce ban risk.
- You can add `fitness.yaml` to `/niches` to swap niches immediately.
- Move to Postgres + a scheduler (APScheduler/Celery) later if needed.
