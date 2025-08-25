import json
import os
import random
import requests
import asyncio
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
account_comment_trackers = {}
last_api_call_time = 0
MIN_API_CALL_INTERVAL = 120


def get_proper_reddit_url(post_data):
    try:
        post_id = post_data.get('id', '')
        subreddit = post_data.get('subreddit', '')

        if post_id and subreddit:
            return f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/"

        provided_url = post_data.get('url', '')
        if 'reddit.com' in provided_url:
            return provided_url
        if post_id:
            return f"https://www.reddit.com/comments/{post_id}/"

        return provided_url

    except Exception as e:
        print(f"⚠️ Error extracting URL: {e}")
        return post_data.get('url', '')


async def handle_rate_limit(headers, db, account):
    if 'x-ratelimit-remaining' in headers and headers['x-ratelimit-remaining'] == '0':
        reset_time = int(headers.get('x-ratelimit-reset', 60))
        print(f"⏰ Rate limit exceeded. Waiting {reset_time} seconds...")
        await asyncio.sleep(reset_time)
        return True
    return False


async def enforce_api_rate_limit():
    global last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - last_api_call_time

    if time_since_last_call < MIN_API_CALL_INTERVAL:
        wait_time = MIN_API_CALL_INTERVAL - time_since_last_call
        print(f"⏰ Enforcing API rate limit: waiting {wait_time:.1f} seconds")
        await asyncio.sleep(wait_time)

    last_api_call_time = time.time()


async def post_comment_with_retry(headers, reddit_id, comment_text, db, account, max_retries=2):
    for attempt in range(max_retries):
        try:
            await enforce_api_rate_limit()

            res = requests.post(
                "https://oauth.reddit.com/api/comment",
                headers=headers,
                data={"thing_id": f"t3_{reddit_id}", "text": comment_text},
                timeout=15
            )

            print(f"Status Code: {res.status_code}")

            try:
                response_data = res.json()
                print("JSON Response:")
                print(json.dumps(response_data, indent=2))
            except ValueError:
                print("Response is not valid JSON")
                response_data = {}

            if res.status_code == 200 and response_data.get('success') is False:
                error_message = "Unknown rate limit error"
                if 'jquery' in response_data:
                    for item in response_data.get('jquery', []):
                        if len(item) >= 4 and isinstance(item[3], list) and len(item[3]) > 0:
                            if any(keyword in str(item[3][0]) for keyword in
                                   ["Take a break", "been doing that a lot", "seconds", "minutes"]):
                                error_message = item[3][0]
                                break

                print(f"❌ Rate limited (attempt {attempt + 1}/{max_retries}): {error_message}")

                wait_time = 30
                if "5 seconds" in error_message:
                    wait_time = 30
                elif "10 seconds" in error_message:
                    wait_time = 60
                elif "30 seconds" in error_message:
                    wait_time = 120
                elif "1 minute" in error_message:
                    wait_time = 220
                elif "2 minutes" in error_message:
                    wait_time = 300
                elif "5 minutes" in error_message:
                    wait_time = 450

                print(f"⏰ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
                continue

            if await handle_rate_limit(res.headers, db, account):
                continue

            if res.status_code == 200 and response_data.get('success', False):
                comment_id = None
                try:
                    if 'json' in response_data and 'data' in response_data['json']:
                        things = response_data['json']['data'].get('things', [])
                        if things and 'data' in things[0]:
                            comment_id = things[0]['data'].get('id')
                    elif 'jquery' in response_data:
                        for item in response_data['jquery']:
                            if (len(item) >= 4 and isinstance(item[3], list) and
                                    len(item[3]) > 0 and isinstance(item[3][0], list) and
                                    len(item[3][0]) > 0 and isinstance(item[3][0][0], dict) and
                                    'data' in item[3][0][0] and 'id' in item[3][0][0]['data']):
                                comment_id = item[3][0][0]['data']['id']
                                break
                except (KeyError, IndexError, TypeError) as e:
                    print(f"⚠️ Could not extract comment ID from response: {e}")
                    comment_id = f"unknown_{int(time.time())}"

                return True, comment_id

            elif res.status_code == 429:
                retry_after = int(res.headers.get('retry-after', 30))
                print(f"⏰ HTTP 429 Too Many Requests. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                continue

            elif res.status_code == 403:
                print("❌ 403 Forbidden -可能需要刷新token或权限不足")
                return False, None

            elif res.status_code == 401:
                print("❌ 401 Unauthorized - Token may be expired")
                try:
                    print("🔄 Refreshing token due to 401 error...")
                    account = refresh_token(account, db)
                    headers["Authorization"] = f"bearer {account.access_token}"
                    print("✅ Token refreshed, retrying...")
                    continue
                except Exception as e:
                    print("❌ Token refresh failed:", e)
                    return False, None

            else:
                print(f"❌ Comment failed with status {res.status_code}: {res.text}")
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(10 * (attempt + 1))
            continue

    print(f"❌ Failed to post comment after {max_retries} attempts")
    return False, None


def can_post_more_comments(account_id):
    now = datetime.now()

    if account_id not in account_comment_trackers:
        account_comment_trackers[account_id] = {
            'count': 0,
            'hour_start': now.replace(minute=0, second=0, microsecond=0)
        }

    tracker = account_comment_trackers[account_id]

    if now - tracker['hour_start'] >= timedelta(hours=1):
        tracker['count'] = 0
        tracker['hour_start'] = now.replace(minute=0, second=0, microsecond=0)
        print(f"🔄 Reset comment counter for account {account_id} for new hour")
    if tracker['count'] >= 2:
        next_reset = tracker['hour_start'] + timedelta(hours=1)
        time_until_reset = next_reset - now
        print(f"⏰ Account {account_id} reached 2 comment limit this hour. Next reset in: {time_until_reset}")
        return False, time_until_reset.total_seconds()

    return True, 0


async def safe_reddit_api_call(url, headers, method='get', data=None):
    await enforce_api_rate_limit()

    try:
        if method == 'get':
            res = requests.get(url, headers=headers, timeout=15)
        else:
            res = requests.post(url, headers=headers, data=data, timeout=15)

        res.raise_for_status()
        return res

    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed: {e}")
        raise


async def process_schedule(sched, db: Session):
    account = db.query(RedditAccount).get(sched.account_id)
    if not account:
        print("⚠️ Account not found, skipping")
        return

    local_now = datetime.now()

    # Check if schedule has ended (end_date is in the past)
    if sched.end_date and sched.end_date < local_now.date():
        print(f"⏭️ Schedule ID={sched.id} has ended (end_date: {sched.end_date}), skipping")
        sched.status = "completed"
        db.commit()
        return

    print(f"➡️ Processing schedule ID={sched.id} for account {account.username}")
    can_post, wait_time = can_post_more_comments(account.id)
    if not can_post:
        print(f"⏭️ Account {account.username} has reached comment limit this hour, skipping")
        return

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

        potential_posts = []
        after = None
        new_count = 0
        max_new = 20

        while new_count < max_new:
            url = f"https://oauth.reddit.com/r/{account.niche}/hot?limit=10"
            if after:
                url += f"&after={after}"

            try:
                res = await safe_reddit_api_call(url, headers, 'get')
                data = res.json().get("data", {})
            except Exception as e:
                print(f"❌ Failed to fetch posts: {e}")
                break

            posts = data.get("children", [])
            print(f"📨 Retrieved {len(posts)} posts (after={after})")

            for post in posts:
                post_data = post["data"]
                reddit_id = post_data["id"]
                original_url = post_data.get('url', '')
                print(f"🔗 Original URL from Reddit: {original_url}")
                proper_url = get_proper_reddit_url(post_data)
                print(f"🔗 Proper URL to save: {proper_url}")

                existing_comment = db.query(RedditComment).filter_by(
                    account_id=account.id,
                    reddit_id=reddit_id
                ).first()

                if not existing_comment:
                    potential_posts.append({
                        "reddit_id": reddit_id,
                        "title": post_data["title"],
                        "body": post_data.get("selftext", ""),
                        "subreddit": post_data["subreddit"],
                        "url": proper_url,
                        "created_utc": post_data["created_utc"],
                        "post_data": post_data
                    })
                    new_count += 1
                    print(f"📝 Post {reddit_id} added to potential posts (new_count={new_count})")

                if new_count >= max_new:
                    break

            if new_count >= max_new:
                break

            after = data.get("after")
            if not after:
                break

            await asyncio.sleep(5)

        print(f"📊 Finished: {new_count} potential posts found")

        commented_posts = []
        failed_posts = []
        comments_posted_this_run = 0
        max_comments_per_run = 1

        for post_info in potential_posts:
            can_post, _ = can_post_more_comments(account.id)
            if not can_post or comments_posted_this_run >= max_comments_per_run:
                print(f"⏹️ Reached comment limit for account {account.username} this run")
                break

            reddit_id = post_info["reddit_id"]

            base_prompt = build_comment_prompt(sched, post_info, account)
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": base_prompt}],
                temperature=0.9,
            )
            comment_text = completion.choices[0].message.content.strip()

            if len(comment_text) < 10 or len(comment_text) > 500:
                continue

            success, comment_id = await post_comment_with_retry(headers, reddit_id, comment_text, db, account)

            if success:
                try:
                    new_post = RedditPost(
                        account_id=account.id,
                        reddit_id=reddit_id,
                        title=post_info["title"],
                        body=post_info["body"],
                        subreddit=post_info["subreddit"],
                        url=post_info["url"],
                        created_utc=post_info["created_utc"]
                    )
                    db.add(new_post)

                    new_comment = RedditComment(
                        account_id=account.id,
                        reddit_id=reddit_id,
                        body=comment_text,
                        created_utc=int(datetime.now().timestamp()),
                        comment_id=comment_id
                    )
                    db.add(new_comment)

                    db.commit()

                    commented_posts.append(reddit_id)
                    comments_posted_this_run += 1

                    if account.id not in account_comment_trackers:
                        account_comment_trackers[account.id] = {
                            'count': 0,
                            'hour_start': datetime.now().replace(minute=0, second=0, microsecond=0)
                        }
                    account_comment_trackers[account.id]['count'] += 1

                    print(f"[{account.username}] ✅ Commented on {reddit_id}: {comment_text[:60]}…")
                    print(
                        f"📊 Account {account.username} has posted {account_comment_trackers[account.id]['count']}/2 comments this hour")

                    wait_between_comments = random.uniform(1800, 2400)
                    print(f"⏰ Waiting {wait_between_comments / 60:.1f} minutes before next comment...")
                    await asyncio.sleep(wait_between_comments)
                except IntegrityError:
                    db.rollback()
                    print(f"⚠️ Duplicate post or comment detected for {reddit_id}")
                    failed_posts.append(reddit_id)
            else:
                failed_posts.append(reddit_id)
                print(f"[{account.username}] ❌ Failed to comment on {reddit_id}")

        if commented_posts:
            sched.excuted = 1
            db.commit()
            print(f"✅ Schedule {sched.id} marked as executed - {len(commented_posts)} comments posted")

            if sched.end_date and sched.end_date < datetime.now().date():
                sched.status = "completed"
                db.commit()
                print(f"🏁 Schedule {sched.id} completed (end_date reached)")
        else:
            print(f"⚠️ Schedule {sched.id} had no successful comments, keeping as pending")

        print(f"😴 Finished processing account {account.username} for this run")

    except Exception as e:
        print("❌ Error in process_schedule:", e)
        db.rollback()
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
            can_post, wait_time = can_post_more_comments(account.id)
            if not can_post:
                print(f"⏭️ Account {account.username} has reached comment limit this hour, skipping")
                continue

            schedules = db.query(RedditSchedule).filter(
                RedditSchedule.account_id == account.id,
                RedditSchedule.status == "pending"
            ).all()

            print(f"👤 Account {account.username} has {len(schedules)} pending schedules")

            if schedules:
                await process_schedule(schedules[0], db)
                wait_time = random.uniform(300, 600)
                print(f"⏰ Waiting {wait_time/60:.1f} minutes before processing next account...")
                await asyncio.sleep(wait_time)

    except Exception as e:
        print("❌ Error in run_schedules:", e)
    finally:
        db.close()


async def reset_executed_daily():
    global assigned_hours, account_windows, account_comment_trackers
    db: Session = SessionLocal()
    try:
        today = datetime.now().date()
        updated = db.query(RedditSchedule).filter(
            (RedditSchedule.end_date == None) | (RedditSchedule.end_date >= today),
            RedditSchedule.status == "pending"
        ).update({"excuted": False}, synchronize_session=False)
        db.commit()
        print(f"🔄 Reset {updated} schedules to executed=False for new day")
        assigned_hours = 0
        account_windows = {}
        account_comment_trackers = {}
        print("♻️ Cleared daily account windows and comment trackers")
    except Exception as e:
        print("❌ Error in reset_executed_daily:", e)
    finally:
        db.close()


async def check_completed_schedules():
    db: Session = SessionLocal()
    try:
        today = datetime.now().date()
        completed = db.query(RedditSchedule).filter(
            RedditSchedule.end_date < today,
            RedditSchedule.status == "pending"
        ).update({"status": "completed"}, synchronize_session=False)
        db.commit()
        if completed > 0:
            print(f"✅ Marked {completed} schedules as completed (end_date reached)")
    except Exception as e:
        print("❌ Error in check_completed_schedules:", e)
    finally:
        db.close()


scheduler = AsyncIOScheduler()
scheduler.add_job(run_schedules, "interval", minutes=10)
scheduler.add_job(reset_executed_daily, "cron", hour=0, minute=0)
scheduler.add_job(check_completed_schedules, "cron", hour=1, minute=0)
scheduler.start()
print("✅ Async Scheduler started (run every 10m, reset daily at midnight, check completed at 1 AM)")



def build_comment_prompt(sched: RedditSchedule, post_info: dict, account: RedditAccount) -> str:
    """
    Priority:
    1) sched.prompt (if non-empty)
    2) default fallback using post title + niche
    Supports placeholders: {title}, {subreddit}, {url}, {niche}
    """
    fallback = (
        "Write a short, natural, human-like Reddit comment relevant to the niche "
        "\"{niche}\" for this post titled \"{title}\"."
    )
    print(sched.prompt)
    print(post_info)
    print(account.niche)
    raw = (sched.prompt or "").strip() or fallback
    return raw.format(
        title=post_info.get("title", ""),
        subreddit=post_info.get("subreddit", ""),
        url=post_info.get("url", ""),
        niche=account.niche or "",
    )
