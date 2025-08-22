import os
import random
import requests
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv

from database.db import SessionLocal
from database.models import RedditSchedule, RedditAccount, RedditPost, RedditComment
from api.reddit import refresh_token

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.5993.117 Safari/537.36"
)

# store daily allowed windows for accounts
account_windows = {}

def get_account_window(account_id):
    today = datetime.now().date()
    if account_id not in account_windows or account_windows[account_id][0].date() != today:
        start_hour = datetime.now().replace(
            hour=random.randint(0, 2), minute=0, second=0, microsecond=0
        )
        end_hour = start_hour + timedelta(hours=random.choice([1, 2]))
        account_windows[account_id] = (start_hour, end_hour)
        print(f"🎲 Assigned daily window for account {account_id}: {start_hour} → {end_hour}")
    return account_windows[account_id]

async def process_schedule(sched, db: Session):
    account = db.query(RedditAccount).get(sched.account_id)
    if not account:
        print("⚠️ Account not found, skipping")
        return

    local_now = datetime.now()
    start_hour, end_hour = get_account_window(account.id)
    # if not (start_hour <= local_now <= end_hour):
    #     print(f"⏭️ Account {account.username} skipped (outside daily window {start_hour.hour}-{end_hour.hour})")
    #     return

    print(f"➡️ Processing schedule ID={sched.id} for account {account.username}")

    # refresh token if needed
    if account.token_expires_at <= local_now:
        try:
            print("🔄 Refreshing token…")
            account = refresh_token(account, db)
            print("✅ Token refreshed")
        except Exception as e:
            print("❌ Refresh token failed:", e)
            return

    headers = {"Authorization": f"bearer {account.access_token}", "User-Agent": USER_AGENT}

    try:
        print(f"🌐 Fetching posts from r/{account.niche}")
        res = requests.get(
            f"https://oauth.reddit.com/r/{account.niche}/hot?limit=5",
            headers=headers, timeout=10
        )
        res.raise_for_status()
        posts = res.json().get("data", {}).get("children", [])
        print(f"📨 Retrieved {len(posts)} posts from r/{account.niche}")
        await asyncio.sleep(5)
    except Exception as e:
        print("❌ Error fetching posts:", e)
        return

    for post in posts:
        reddit_id = post["data"]["id"]
        if db.query(RedditComment).filter_by(account_id=account.id, reddit_id=reddit_id).first():
            continue

        base_prompt = sched.prompt or f"Write a short, human-like Reddit comment for:\n\n{post['data']['title']}"
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": base_prompt}],
            temperature=0.9,
        )
        comment_text = completion.choices[0].message.content.strip()

        if len(comment_text) < 10 or len(comment_text) > 500:
            continue

        try:
            res = requests.post(
                "https://oauth.reddit.com/api/comment",
                headers=headers,
                data={"thing_id": f"t3_{reddit_id}", "text": comment_text},
                timeout=10
            )
            if res.status_code == 200:
                db.add(RedditComment(
                    account_id=account.id,
                    reddit_id=reddit_id,
                    body=comment_text,
                    created_utc=int(datetime.now().timestamp())
                ))
                db.commit()
                print(f"[{account.username}] ✅ Commented on {reddit_id}: {comment_text[:60]}…")
                await asyncio.sleep(10)
        except Exception as e:
            print("❌ Error posting comment:", e)

    # ✅ mark this schedule as executed + done
    sched.status = "done"
    sched.executed = True
    db.commit()
    print(f"✅ Schedule {sched.id} marked as done & executed")

    # check if all schedules for this account are completed
    pending = db.query(RedditSchedule).filter(
        RedditSchedule.account_id == account.id,
        RedditSchedule.status != "completed"
    ).count()
    if pending == 0:
        sched.status = "completed"
        db.commit()
        print(f"🏁 All schedules done for account {account.username} → status set to completed")

async def run_schedules():
    db: Session = SessionLocal()
    print("⚡ run_schedules triggered at", datetime.now())
    try:
        local_now = datetime.now()

        schedules = db.query(RedditSchedule).filter(
            RedditSchedule.status == "pending",
            (RedditSchedule.start_date == None) | (RedditSchedule.start_date <= local_now.date()),
            (RedditSchedule.end_date == None) | (RedditSchedule.end_date >= local_now.date())
        ).all()

        print(f"📋 Found {len(schedules)} pending schedules")
        tasks = [process_schedule(s, db) for s in schedules]
        if tasks:
            await asyncio.gather(*tasks)
    except Exception as e:
        print("❌ Error in run_schedules:", e)
    finally:
        db.close()

async def reset_executed_daily():
    """Reset executed=False for valid schedules every midnight."""
    db: Session = SessionLocal()
    try:
        today = datetime.now().date()
        updated = db.query(RedditSchedule).filter(
            RedditSchedule.end_date == None
            | (RedditSchedule.end_date >= today)
        ).update({"executed": False}, synchronize_session=False)
        db.commit()
        print(f"🔄 Reset {updated} schedules to executed=False for new day")
    except Exception as e:
        print("❌ Error in reset_executed_daily:", e)
    finally:
        db.close()

# scheduler setup
scheduler = AsyncIOScheduler()
scheduler.add_job(run_schedules, "interval", minutes=1)
scheduler.add_job(reset_executed_daily, "cron", hour=0, minute=0)  # reset at midnight
scheduler.start()
print("✅ Async Scheduler started (run every 1m, reset daily at midnight)")
