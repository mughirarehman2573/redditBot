import os
import random
import asyncio
import time
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv
import asyncpraw
import asyncprawcore
import aiohttp
import threading

from database.db import SessionLocal
from database.models import RedditSchedule, RedditAccount, RedditPost, RedditComment
from api.reddit import refresh_token

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

account_windows = {}
assigned_hours = 0
account_comment_trackers = {}
last_api_call_time = 0
MIN_API_CALL_INTERVAL = 120
account_next_comment_time = {}
account_post_trackers = {}
processed_posts_cache = {}
processing_lock = threading.Lock()
global_rate_limit_cooldown = None


def get_user_agent(account):
    """Generate a custom user agent for each account"""
    return f"golfagent by u/{account.username} v1.0"


def get_proper_reddit_url(post_data):
    """Extract proper Reddit URL from post data"""
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


def is_global_cooldown_active():
    """Check if global cooldown is active"""
    global global_rate_limit_cooldown
    if global_rate_limit_cooldown is None:
        return False

    time_remaining = global_rate_limit_cooldown - time.time()
    if time_remaining > 0:
        return True, time_remaining
    else:
        global_rate_limit_cooldown = None
        return False, 0


def set_global_cooldown(duration_hours=2):
    """Set global cooldown for all operations"""
    global global_rate_limit_cooldown
    global_rate_limit_cooldown = time.time() + (duration_hours * 3600)
    print(f"🛑 GLOBAL COOLDOWN ACTIVATED: No operations for {duration_hours} hours")
    print(f"⏰ Cooldown ends at: {datetime.fromtimestamp(global_rate_limit_cooldown)}")


async def enforce_api_rate_limit():
    """Enforce minimum time between API calls"""
    global last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - last_api_call_time

    if time_since_last_call < MIN_API_CALL_INTERVAL:
        wait_time = MIN_API_CALL_INTERVAL - time_since_last_call
        print(f"⏰ Enforcing API rate limit: waiting {wait_time:.1f} seconds")
        await asyncio.sleep(wait_time)

    last_api_call_time = time.time()


async def post_comment_with_retry_asyncpraw(reddit_client, reddit_id, comment_text, db, account, max_retries=2):
    """Post comment with retry logic using Async PRAW"""
    for attempt in range(max_retries):
        try:
            await enforce_api_rate_limit()

            submission = await reddit_client.submission(id=reddit_id)

            existing_comment = db.query(RedditComment).filter_by(
                account_id=account.id,
                reddit_id=reddit_id
            ).first()

            if existing_comment:
                print(f"⏭️ Already commented on post {reddit_id}, skipping")
                return False, None

            comment = await submission.reply(comment_text)

            print(f"✅ Comment posted successfully with Async PRAW")
            return True, comment.id

        except asyncprawcore.exceptions.Forbidden as e:
            print(f"❌ Forbidden error (possibly banned): {e}")
            return False, None

        except asyncprawcore.exceptions.AsyncPrawcoreException as e:
            if "RATELIMIT" in str(e).upper():
                print(f"❌ RATE LIMIT ERROR (attempt {attempt + 1}/{max_retries}): {e}")

                set_global_cooldown(2)
                return False, None
            else:
                print(f"❌ Async PRAW API error: {e}")
                return False, None

        except Exception as e:
            print(f"❌ Error posting comment with Async PRAW (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(10 * (attempt + 1))
            continue

    print(f"❌ Failed to post comment after {max_retries} attempts")
    return False, None


def get_account_hourly_comment_limit(account_created_dt):
    """Return hourly comment limit based on account age"""
    account_age_days = (datetime.now() - account_created_dt).days

    if account_age_days < 7:
        return 1
    elif account_age_days < 14:
        return 2
    elif account_age_days < 30:
        return 3
    else:
        return 4


def can_post_more_comments(account_id, account_created_dt):
    """Check if account can post more comments within hourly limit based on account age"""
    now = datetime.now()
    hourly_limit = get_account_hourly_comment_limit(account_created_dt)

    if account_id not in account_comment_trackers:
        account_comment_trackers[account_id] = {
            'count': 0,
            'hour_start': now.replace(minute=0, second=0, microsecond=0),
            'hourly_limit': hourly_limit,
            'last_comment_time': None
        }

    tracker = account_comment_trackers[account_id]
    tracker['hourly_limit'] = hourly_limit

    if now - tracker['hour_start'] >= timedelta(hours=1):
        tracker['count'] = 0
        tracker['hour_start'] = now.replace(minute=0, second=0, microsecond=0)
        print(f"🔄 Reset comment counter for account {account_id} for new hour (limit: {hourly_limit}/hour)")

    if tracker['last_comment_time'] and (now - tracker['last_comment_time']).total_seconds() < 3600:
        time_until_next = 3600 - (now - tracker['last_comment_time']).total_seconds()
        print(f"⏰ Account {account_id} already commented in last hour. Wait {time_until_next / 60:.1f} minutes")
        return False, time_until_next

    if tracker['count'] >= hourly_limit:
        next_reset = tracker['hour_start'] + timedelta(hours=1)
        time_until_reset = next_reset - now
        print(
            f"⏰ Account {account_id} reached {hourly_limit} comment limit this hour. Next reset in: {time_until_reset}")
        return False, time_until_reset.total_seconds()

    return True, 0


def is_post_processed(account_id, post_id):
    """Check if this post has been processed recently for this account"""
    cache_key = f"{account_id}_{post_id}"
    current_time = time.time()

    for key in list(processed_posts_cache.keys()):
        if current_time - processed_posts_cache[key] > 86400:
            del processed_posts_cache[key]

    return cache_key in processed_posts_cache


def mark_post_processed(account_id, post_id):
    """Mark a post as processed for this account"""
    cache_key = f"{account_id}_{post_id}"
    processed_posts_cache[cache_key] = time.time()


async def process_schedule(sched, db: Session):
    """Process a schedule for posting comments"""
    cooldown_active, time_remaining = is_global_cooldown_active()
    if cooldown_active:
        print(f"🛑 GLOBAL COOLDOWN ACTIVE: Skipping all operations for {time_remaining / 3600:.1f} more hours")
        return

    account = db.query(RedditAccount).get(sched.account_id)
    if not account:
        print("⚠️ Account not found or inactive, skipping")
        return

    local_now = datetime.now()

    if sched.end_date and sched.end_date < local_now.date():
        print(f"⏭️ Schedule ID={sched.id} has ended (end_date: {sched.end_date}), skipping")
        sched.status = "completed"
        db.commit()
        return

    can_post, wait_time = can_post_more_comments(account.id, account.created_at)
    if not can_post:
        print(f"⏭️ Account {account.username} has reached comment limit this hour, skipping")
        return

    if account.token_expires_at <= local_now:
        try:
            print("🔄 Refreshing token…")
            result = refresh_token(account, db)

            if isinstance(result, dict):
                account.access_token = result.get('access_token')
                account.refresh_token = result.get('refresh_token', account.refresh_token)
                account.token_expires_at = datetime.fromtimestamp(result.get('expires_at', time.time() + 3600))
                db.commit()
                print("✅ Token refreshed and account updated")
            else:
                account = result
                print("✅ Token refreshed")

        except Exception as e:
            print("❌ Refresh token failed:", e)
            return

    session = None
    reddit = None

    try:
        user_agent = get_user_agent(account)
        session = aiohttp.ClientSession(trust_env=True)
        reddit = asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            refresh_token=account.refresh_token,
            user_agent=user_agent,
            timeout=30,
            requestor_kwargs={"session": session},
            check_for_updates=False
        )

        me = await reddit.user.me()
        print(f"✅ Async PRAW client initialized for {account.username} with user agent: {user_agent}")

    except Exception as e:
        print(f"❌ Failed to initialize Async PRAW client for {account.username}: {e}")
        if session:
            await session.close()
        return

    try:
        print(f"🌐 Fetching posts from r/{account.niche}")
        subreddit_name = normalize_subreddit(account.niche)
        potential_posts = []
        new_count = 0
        max_new = 15
        max_post_age_days = 7

        try:
            subreddit = await reddit.subreddit(subreddit_name)
            async for submission in subreddit.hot(limit=25):
                cooldown_active, _ = is_global_cooldown_active()
                if cooldown_active:
                    print("🛑 Global cooldown activated during post fetching, stopping")
                    break

                if submission.stickied:
                    continue

                post_data = {
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "subreddit": str(submission.subreddit),
                    "url": submission.url,
                    "created_utc": submission.created_utc,
                    "score": submission.score,
                    "num_comments": submission.num_comments
                }

                if post_data["score"] < 5 or post_data["num_comments"] > 50:
                    continue

                post_age_days = (datetime.now() - datetime.fromtimestamp(post_data["created_utc"])).days
                if post_age_days > max_post_age_days:
                    continue

                if is_post_processed(account.id, post_data["id"]):
                    continue

                existing_comment = db.query(RedditComment).filter_by(
                    account_id=account.id,
                    reddit_id=post_data["id"]
                ).first()

                if not existing_comment:
                    proper_url = get_proper_reddit_url(post_data)
                    potential_posts.append({
                        "reddit_id": post_data["id"],
                        "title": post_data["title"],
                        "body": post_data.get("selftext", ""),
                        "subreddit": post_data["subreddit"],
                        "url": proper_url,
                        "created_utc": post_data["created_utc"],
                        "post_data": post_data
                    })
                    new_count += 1
                    print(f"📝 Post {post_data['id']} added to potential posts (new_count={new_count})")

                if new_count >= max_new:
                    break

        except Exception as e:
            print(f"❌ Failed to fetch posts with Async PRAW: {e}")
            await reddit.close()
            if session:
                await session.close()
            return

        print(f"📊 Finished: {new_count} potential posts found")

        if not potential_posts:
            print(f"⏭️ No suitable posts found for {account.username}, skipping")
            await reddit.close()
            if session:
                await session.close()
            return

        commented_posts = []
        failed_posts = []
        comments_posted_this_run = 0
        hourly_limit = get_account_hourly_comment_limit(account.created_at)
        max_comments_per_run = 1

        random.shuffle(potential_posts)

        for post_info in potential_posts:
            cooldown_active, _ = is_global_cooldown_active()
            if cooldown_active:
                print("🛑 Global cooldown activated, stopping all operations")
                break

            if comments_posted_this_run >= max_comments_per_run:
                break

            reddit_id = post_info["reddit_id"]
            mark_post_processed(account.id, reddit_id)

            base_prompt = build_comment_prompt(sched, post_info, account)
            try:
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": base_prompt}],
                    temperature=0.9,
                )
                comment_text = completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"❌ OpenAI API error: {e}")
                continue

            if len(comment_text) < 15 or len(comment_text) > 300:
                print(f"⚠️ Comment length invalid ({len(comment_text)} chars), skipping")
                continue

            if any(phrase in comment_text.lower() for phrase in ["i'm", "i am", "as an ai", "as a language model"]):
                print(f"⚠️ AI-sounding comment detected, skipping")
                continue

            success, comment_id = await post_comment_with_retry_asyncpraw(reddit, reddit_id, comment_text, db, account)

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
                            'hour_start': datetime.now().replace(minute=0, second=0, microsecond=0),
                            'hourly_limit': hourly_limit,
                            'last_comment_time': datetime.now()
                        }
                    account_comment_trackers[account.id]['count'] += 1
                    account_comment_trackers[account.id]['last_comment_time'] = datetime.now()

                    print(f"[{account.username}] ✅ Commented on {reddit_id}: {comment_text[:60]}…")
                    print(
                        f"📊 Account {account.username} has posted {account_comment_trackers[account.id]['count']}/{hourly_limit} comments this hour")

                    break

                except IntegrityError:
                    db.rollback()
                    print(f"⚠️ Duplicate post or comment detected for {reddit_id}")
                    failed_posts.append(reddit_id)
            else:
                failed_posts.append(reddit_id)
                print(f"[{account.username}] ❌ Failed to comment on {reddit_id}")

        if commented_posts:
            if sched.end_date and sched.end_date < datetime.now().date():
                sched.excuted = 1
                sched.status = "completed"
                db.commit()
                print(f"🏁 Schedule {sched.id} completed (end_date reached)")
        else:
            print(f"⚠️ Schedule {sched.id} had no successful comments, keeping as pending")

        print(f"😴 Finished processing account {account.username} for this run")

        await reddit.close()
        if session:
            await session.close()

    except Exception as e:
        print("❌ Error in process_schedule:", e)
        db.rollback()
        try:
            await reddit.close()
        except Exception:
            pass
        if session:
            await session.close()
        return


async def run_schedules():
    """Main function to run all schedules"""
    cooldown_active, time_remaining = is_global_cooldown_active()
    if cooldown_active:
        print(f"🛑 GLOBAL COOLDOWN ACTIVE: Skipping run_schedules for {time_remaining / 3600:.1f} more hours")
        return

    if not processing_lock.acquire(blocking=False):
        print("⏭️ Another schedule run is already in progress, skipping")
        return

    db: Session = SessionLocal()
    print("⚡ run_schedules triggered at", datetime.now())

    try:
        accounts = db.query(RedditAccount).join(RedditSchedule).filter(
            RedditSchedule.status == "pending",
        ).all()

        print(f"📋 Found {len(accounts)} accounts with pending schedules")

        if not accounts:
            print("⏭️ No accounts with pending schedules, skipping")
            return

        random.shuffle(accounts)

        for account in accounts:
            cooldown_active, _ = is_global_cooldown_active()
            if cooldown_active:
                print("🛑 Global cooldown activated during account processing, stopping")
                break

            can_post, wait_time = can_post_more_comments(account.id, account.created_at)
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
                print(f"⏰ Waiting {wait_time / 60:.1f} minutes before processing next account...")
                await asyncio.sleep(wait_time)

    except Exception as e:
        print("❌ Error in run_schedules:", e)
    finally:
        db.close()
        processing_lock.release()

async def reset_executed_daily():
    """Reset daily execution counters"""
    global assigned_hours, account_windows, account_comment_trackers, account_next_comment_time
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
        account_next_comment_time = {}
        print("♻️ Cleared daily account windows, comment trackers, and timing schedules")
    except Exception as e:
        print("❌ Error in reset_executed_daily:", e)
    finally:
        db.close()


async def check_completed_schedules():
    """Check and mark completed schedules"""
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


async def simulate_human_activity():
    """Simulate human-like activity (browsing, upvoting)"""
    db: Session = SessionLocal()
    try:
        account = db.query(RedditAccount).filter(
        ).order_by(db.func.random()).first()

        if not account:
            return

        print(f"👤 Simulating human activity for {account.username}")

        user_agent = get_user_agent(account)
        session = aiohttp.ClientSession(trust_env=True)
        reddit = asyncpraw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            refresh_token=account.refresh_token,
            user_agent=user_agent,
            timeout=30,
            requestor_kwargs={"session": session},
            check_for_updates=False
        )

        subreddits = ["popular", "all", account.niche]
        subreddit_name = random.choice(subreddits)

        try:
            subreddit = await reddit.subreddit(subreddit_name)
            print(f"🌐 Browsing r/{subreddit_name} with {account.username}")

            async for submission in subreddit.hot(limit=random.randint(3, 8)):
                if random.random() < 0.2:
                    try:
                        await submission.upvote()
                        print(f"⬆️ Upvoted a post in r/{subreddit_name}")
                        await asyncio.sleep(random.uniform(1, 3))
                    except Exception:
                        pass

                await asyncio.sleep(random.uniform(2, 8))

            print(f"✅ Finished browsing with {account.username}")

        except Exception as e:
            print(f"❌ Error during human activity simulation: {e}")

        await reddit.close()
        await session.close()

    except Exception as e:
        print("❌ Error in simulate_human_activity:", e)
    finally:
        db.close()


def build_comment_prompt(sched: RedditSchedule, post_info: dict, account: RedditAccount) -> str:
    """Build prompt for OpenAI to generate comments"""
    title = post_info.get("title", "")
    body = post_info.get("body", "")
    custom_prompt = (sched.prompt or "").strip()
    niche = account.niche or ""

    if custom_prompt:
        return f"""
        {custom_prompt}

        Here is the post you're responding to:

        POST TITLE: {title}

        POST CONTENT:
        {body}

        Keep your response focused on the context of {niche}.

        IMPORTANT: 
        - Do not use quotation marks in your response
        - Do not mention that you're an AI or language model
        - Keep it natural and human-like
        - Avoid repetitive phrases

        Write your comment:
        """
    else:
        return f"""
        Write a helpful, empathetic, and professional comment for this Reddit post in the r/{post_info.get('subreddit', '')} subreddit.

        POST TITLE: {title}

        POST CONTENT:
        {body}

        Your response should be:
        - Relevant to the specific post content
        - Helpful and informative
        - Professional but empathetic  
        - Concise (1-2 sentences maximum)
        - No emojis or quotation marks
        - Focused on providing genuine value
        - Stay within the context of {niche}
        - Sound like a real person, not an AI

        IMPORTANT: 
        - Do not use quotation marks in the response
        - Do not mention that you're an AI or language model
        - Keep it natural and human-like

        Write your comment:
        """

def normalize_subreddit(name: str) -> str:
    """Normalize subreddit name"""
    return name.lower().replace("'", "").replace(" ", "")
