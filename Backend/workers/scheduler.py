import os
import time
import random
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv

from database.db import SessionLocal
from database.models import RedditSchedule, RedditAccount, RedditPost, RedditComment
from api.reddit import refresh_token

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

USER_AGENT = "mybot/0.0.1"

def run_schedules():
    db: Session = SessionLocal()
    try:
        # use local time instead of UTC
        now = datetime.now()

        schedules = db.query(RedditSchedule).filter(
            RedditSchedule.run_at <= now,
            RedditSchedule.status == "pending",
            (RedditSchedule.start_date == None) | (RedditSchedule.start_date <= now),
            (RedditSchedule.end_date == None) | (RedditSchedule.end_date >= now)
        ).all()

        for sched in schedules:
            account = db.query(RedditAccount).get(sched.account_id)
            if not account:
                continue

            if account.token_expires_at <= now:
                try:
                    account = refresh_token(account, db)
                except Exception as e:
                    print("Refresh token failed:", e)
                    continue

            headers = {"Authorization": f"bearer {account.access_token}", "User-Agent": USER_AGENT}

            try:
                res = requests.get(
                    f"https://oauth.reddit.com/r/{account.niche}/hot?limit=5",
                    headers=headers, timeout=10
                )
                res.raise_for_status()
                posts = res.json().get("data", {}).get("children", [])
                time.sleep(10)
            except Exception as e:
                print("Error fetching posts:", e)
                continue

            for post in posts:
                reddit_id = post["data"]["id"]

                if db.query(RedditComment).filter_by(
                    account_id=account.id,
                    reddit_id=reddit_id
                ).first():
                    continue

                if not db.query(RedditPost).filter_by(account_id=account.id, reddit_id=reddit_id).first():
                    db.add(RedditPost(
                        account_id=account.id,
                        reddit_id=reddit_id,
                        title=post["data"]["title"],
                        body=post["data"].get("selftext", ""),
                        created_utc=post["data"]["created_utc"]
                    ))
                    db.commit()

                base_prompt = sched.prompt or f"Write a short, human-like Reddit comment for:\n\n{post['data']['title']}"
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": base_prompt}],
                    temperature=0.9,
                )
                comment_text = completion.choices[0].message.content.strip()

                if len(comment_text) < 10 or len(comment_text) > 500:
                    continue
                if any(word in comment_text.lower() for word in ["buy", "discount", "promo", "visit my"]):
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
                            created_utc=int(datetime.now().timestamp())  # local time
                        ))
                        db.commit()
                        print(f"[{account.username}] ✅ Commented on {reddit_id}: {comment_text[:60]}…")
                        time.sleep(10)
                except Exception as e:
                    print("Error posting comment:", e)

            sched.status = "done"
            db.commit()
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(run_schedules, "interval", minutes=1)
scheduler.start()
