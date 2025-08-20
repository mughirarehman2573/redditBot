# backend/app/tasks/celery_worker.py
from celery import Celery
from celery.schedules import crontab
import time
import random
from datetime import datetime
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models import TaskSchedule
from backend.app.models import RedditAccount
from backend.app.models import ContentPool
from backend.app.models import ActivityLog
from backend.app.services import reddit_poster
from backend.app.services.content_service import generate_content_from_pool
from backend.app.services.task_service import get_due_schedules, update_next_run_time
from backend.app.services.activity_service import create_activity_log


celery_app = Celery(
    'reddit_automation',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.celery_worker']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_always_eager=False,
)


@celery_app.task
def execute_scheduled_task(task_id: int):
    """Execute a scheduled task with actual Reddit posting (sync-safe)."""
    db = SessionLocal()
    try:
        task = db.query(TaskSchedule).filter(TaskSchedule.id == task_id).first()
        if not task or not task.is_active:
            return {"status": "skipped", "reason": "inactive"}

        account = db.query(RedditAccount).filter(RedditAccount.id == task.account_id).first()
        if not account or account.status != "active":
            return {"status": "skipped", "reason": "account_inactive"}

        # Add randomization delay if enabled
        if task.randomize_timing:
            delay_seconds = random.randint(0, task.time_variance * 60)
            time.sleep(delay_seconds)

        # Generate content if content pool is specified
        content_text = "Automated content"
        if task.content_pool_id:
            content_result = generate_content_from_pool(db, task.content_pool_id, task.user_id)
            content_text = (
                content_result.get("content") if isinstance(content_result, dict)
                else str(content_result)
            )

        # Run Reddit action
        if task.task_type == "post":
            result = reddit_poster.create_post(
                db, task.account_id, "testsubreddit", f"Scheduled: {task.name}", content_text
            )
        elif task.task_type == "comment":
            result = reddit_poster.create_comment(
                db, task.account_id, "test_submission_id", content_text
            )
        else:
            result = {"status": "skipped", "reason": "unknown_task_type"}

        # Update account stats
        if task.task_type == "post":
            account.total_posts += 1
        elif task.task_type == "comment":
            account.total_comments += 1
        account.last_activity = datetime.now()

        # Update next run time
        update_next_run_time(db, task)

        db.commit()
        return {"status": "success", "task_id": task_id, "result": result}

    except Exception as e:
        # Log error
        create_activity_log(db, task.user_id if task else None, {
            "action_type": task.task_type if task else "unknown",
            "status": "failure",
            "error_message": str(e),
            "account_id": task.account_id if task else None,
            "schedule_id": task.id if task else None
        })
        db.commit()
        return {"status": "error", "error": str(e)}

    finally:
        db.close()


@celery_app.task
def check_due_schedules():
    """Check for schedules that are due to run."""
    db = SessionLocal()
    try:
        due_schedules = get_due_schedules(db)
        for schedule in due_schedules:
            execute_scheduled_task.delay(schedule.id)
            print(f"Queued task {schedule.id} for execution")
        return {"status": "checked", "due_schedules": len(due_schedules)}

    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


# Periodic task to check for due schedules every minute
celery_app.conf.beat_schedule = {
    'check-due-schedules-every-minute': {
        'task': 'app.tasks.celery_worker.check_due_schedules',
        'schedule': crontab(minute='*'),  # Run every minute
    },
}
