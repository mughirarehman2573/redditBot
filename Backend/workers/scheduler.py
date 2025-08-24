import os
import random
import requests
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import or_, cast, func, Date
from sqlalchemy.exc import IntegrityError
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

account_windows = {}
assigned_hours = 0


# def get_account_window(account_id):
#     """Assign sequential daily 1–2 hour window per account within 00–23"""
#     global assigned_hours
#     today = datetime.now().date()
#
#     if account_id not in account_windows or account_windows[account_id][0].date() != today:
#         duration = random.choice([1, 2])
#         start_hour = assigned_hours
#         end_hour = assigned_hours + duration
#
#         if end_hour > 23:
#             print("⚠️ No more slots available today between 00–23")
#             return None
#
#         start_dt = datetime.combine(today, datetime.min.time()).replace(hour=start_hour)
#         end_dt = datetime.combine(today, datetime.min.time()).replace(hour=end_hour)
#
#         account_windows[account_id] = (start_dt, end_dt)
#         assigned_hours = end_hour
#
#         print(f"⏰ Account {account_id} assigned {start_dt.strftime('%H:%M')} → {end_dt.strftime('%H:%M')}")
#
#     return account_windows.get(account_id)


async def process_schedule(sched, db: Session):
    account = db.query(RedditAccount).get(sched.account_id)
    if not account:
        print("⚠️ Account not found, skipping")
        return

    local_now = datetime.now()
    # start_hour, end_hour = get_account_window(account.id)
    # Only proceed if current time is within account's daily window
    # if not (start_hour <= local_now <= end_hour):
    #     print(f"⏭️ Account {account.username} skipped (outside daily window {start_hour.hour}-{end_hour.hour})")
    #     return

    print(f"➡️ Processing schedule ID={sched.id} for account {account.username}")

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

        all_posts = []
        after = None
        new_count = 0
        max_new = 60

        while new_count < max_new:
            url = f"https://oauth.reddit.com/r/{account.niche}/hot?limit=20"
            if after:
                url += f"&after={after}"

            print(f"🐚 curl -X GET \"{url}\" \\")
            print(f"     -H \"Authorization: bearer {account.access_token}\" \\")
            print(f"     -H \"User-Agent: {USER_AGENT}\"")

            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json().get("data", {})

            posts = data.get("children", [])
            print(f"📨 Retrieved {len(posts)} posts (after={after})")

            for post in posts:
                reddit_id = post["data"]["id"]

                existing_post = db.query(RedditPost).filter_by(
                    reddit_id=reddit_id,
                    account_id=account.id
                ).first()

                if not existing_post:
                    try:
                        db.add(RedditPost(
                            account_id=account.id,
                            reddit_id=reddit_id,
                            title=post["data"]["title"],
                            body=post["data"].get("selftext", ""),
                            subreddit=post["data"]["subreddit"],
                            url=post["data"]["url"],
                            created_utc=post["data"]["created_utc"]
                        ))
                        db.commit()
                        new_count += 1
                        all_posts.append(post)
                        print(f"✅ Saved new post {reddit_id} (new_count={new_count})")
                    except IntegrityError:
                        db.rollback()
                        print(f"⚠️ Duplicate skipped (account={account.id}, reddit_id={reddit_id})")
                else:
                    existing_comment = db.query(RedditComment).filter_by(
                        account_id=account.id,
                        reddit_id=reddit_id
                    ).first()
                    if not existing_comment:
                        new_count += 1
                        all_posts.append(post)
                        print(f"📝 Existing post {reddit_id} has no comment yet, will comment (new_count={new_count})")

                if new_count >= max_new:
                    break

            if new_count >= max_new:
                break

            after = data.get("after")
            if not after:
                break

            await asyncio.sleep(3)

        print(f"📊 Finished: {new_count} usable posts, {len(all_posts)} in memory")

        for post in all_posts:
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

        sched.status = "done"
        sched.excuted = 1
        db.commit()
        print(f"✅ Schedule {sched.id} marked as done & executed")

        pending = db.query(RedditSchedule).filter(
            RedditSchedule.account_id == account.id,
            RedditSchedule.status != "completed"
        ).count()
        if pending == 0:
            sched.status = "completed"
            db.commit()
            print(f"🏁 All schedules done for account {account.username} → status set to completed")

        print(f"😴 Sleeping 5 minutes after finishing comments for account {account.username}")
        await asyncio.sleep(300)

    except Exception as e:
        print("❌ Error fetching posts:", e)
        return



async def run_schedules():
    db: Session = SessionLocal()
    print("⚡ run_schedules triggered at", datetime.now())
    try:
        accounts = db.query(RedditAccount).join(RedditSchedule).filter(
            RedditSchedule.status == "pending"
        ).all()

        print(f"📋 Found {len(accounts)} accounts with pending schedules")

        for account in accounts:
            schedules = db.query(RedditSchedule).filter(
                RedditSchedule.account_id == account.id,
                RedditSchedule.status == "pending"
            ).all()

            print(f"👤 Account {account.username} has {len(schedules)} pending schedules")

            tasks = [process_schedule(s, db) for s in schedules]
            if tasks:
                await asyncio.gather(*tasks)

    except Exception as e:
        print("❌ Error in run_schedules:", e)
    finally:
        db.close()


async def reset_executed_daily():
    """Reset executed=False for valid schedules every midnight & reset slots"""
    global assigned_hours, account_windows
    db: Session = SessionLocal()
    try:
        today = datetime.now().date()
        updated = db.query(RedditSchedule).filter(
            (RedditSchedule.end_date == None) | (RedditSchedule.end_date >= today)
        ).update({"excuted": False}, synchronize_session=False)
        db.commit()
        print(f"🔄 Reset {updated} schedules to executed=False for new day")
        assigned_hours = 0
        account_windows = {}
        print("♻️ Cleared daily account windows")
    except Exception as e:
        print("❌ Error in reset_executed_daily:", e)
    finally:
        db.close()


# scheduler setup
scheduler = AsyncIOScheduler()
scheduler.add_job(run_schedules, "interval", minutes=1)
scheduler.add_job(reset_executed_daily, "cron", hour=0, minute=0)
scheduler.start()
print("✅ Async Scheduler started (run every 1m, reset daily at midnight)")
