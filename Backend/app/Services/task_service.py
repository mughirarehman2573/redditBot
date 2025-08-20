# backend/app/services/task_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
import random
from backend.app.models.models import TaskSchedule
from backend.app.models.models import RedditAccount
from backend.app.models.models import User
from backend.app.models.models import Niche
from backend.app.schemas.task_schedule import TaskScheduleCreate, TaskScheduleUpdate


def get_task_schedules_for_user(db: Session, user_id: int):
    """Get all task schedules for a user."""
    return db.query(TaskSchedule).filter(TaskSchedule.user_id == user_id).all()


def get_task_schedule_by_id(db: Session, schedule_id: int, user_id: int):
    """Get a specific task schedule if it belongs to the user."""
    schedule = db.query(TaskSchedule).filter(
        TaskSchedule.id == schedule_id,
        TaskSchedule.user_id == user_id
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task schedule not found"
        )
    return schedule


def create_task_schedule(db: Session, user_id: int, schedule_data: TaskScheduleCreate):
    """Create a new task schedule."""
    # Verify account belongs to user
    account = db.query(RedditAccount).filter(
        RedditAccount.id == schedule_data.account_id,
        RedditAccount.user_id == user_id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account ID"
        )

    # Verify content pool belongs to user if provided
    if schedule_data.content_pool_id:
        from backend.app.models.content_pool import ContentPool
        content_pool = db.query(ContentPool).filter(
            ContentPool.id == schedule_data.content_pool_id,
            ContentPool.user_id == user_id
        ).first()

        if not content_pool:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content pool ID"
            )

    # Calculate next run time
    next_run_time = _calculate_next_run_time(
        schedule_data.frequency_type,
        schedule_data.frequency_value,
        schedule_data.start_time
    )

    # Create the task schedule
    db_schedule = TaskSchedule(
        **schedule_data.dict(),
        user_id=user_id,
        next_run_time=next_run_time
    )

    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


def update_task_schedule(db: Session, schedule_id: int, user_id: int, update_data: TaskScheduleUpdate):
    """Update a task schedule."""
    schedule = get_task_schedule_by_id(db, schedule_id, user_id)

    # Update fields
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(schedule, field, value)

    # Recalculate next run time if frequency changed
    if update_data.frequency_type or update_data.frequency_value:
        schedule.next_run_time = _calculate_next_run_time(
            schedule.frequency_type,
            schedule.frequency_value,
            schedule.start_time
        )

    db.commit()
    db.refresh(schedule)
    return schedule


def delete_task_schedule(db: Session, schedule_id: int, user_id: int):
    """Delete a task schedule."""
    schedule = get_task_schedule_by_id(db, schedule_id, user_id)
    db.delete(schedule)
    db.commit()
    return {"message": "Task schedule deleted successfully"}


def get_due_schedules(db: Session):
    """Get all schedules that are due to run."""
    now = datetime.now()
    return db.query(TaskSchedule).filter(
        TaskSchedule.is_active == True,
        TaskSchedule.next_run_time <= now
    ).all()


def update_next_run_time(db: Session, schedule: TaskSchedule):
    """Update the next run time for a schedule."""
    schedule.next_run_time = _calculate_next_run_time(
        schedule.frequency_type,
        schedule.frequency_value,
        datetime.now()
    )
    db.commit()
    return schedule


def _calculate_next_run_time(frequency_type: str, frequency_value: int, base_time: datetime) -> datetime:
    """Calculate the next run time based on frequency."""
    if frequency_type == "hourly":
        return base_time + timedelta(hours=frequency_value)
    elif frequency_type == "daily":
        return base_time + timedelta(days=frequency_value)
    elif frequency_type == "weekly":
        return base_time + timedelta(weeks=frequency_value)
    else:
        return base_time + timedelta(hours=1)  # Default to hourly