# backend/app/api/endpoints/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.session import get_db
from backend.app.api.dependencies import get_current_user
from backend.app.models.models import User
from backend.app.schemas.task_schedule import TaskSchedule, TaskScheduleCreate, TaskScheduleUpdate
from backend.app.services.task_service import (
    get_task_schedules_for_user,
    get_task_schedule_by_id,
    create_task_schedule,
    update_task_schedule,
    delete_task_schedule
)

router = APIRouter()

@router.get("/", response_model=List[TaskSchedule])
def list_task_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all task schedules for the current user."""
    schedules = get_task_schedules_for_user(db, current_user.id)
    return schedules

@router.get("/{schedule_id}", response_model=TaskSchedule)
def get_task_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific task schedule by ID."""
    return get_task_schedule_by_id(db, schedule_id, current_user.id)

@router.post("/", response_model=TaskSchedule)
def create_task_schedule_endpoint(
    schedule_data: TaskScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task schedule."""
    return create_task_schedule(db, current_user.id, schedule_data)

@router.put("/{schedule_id}", response_model=TaskSchedule)
def update_task_schedule_endpoint(
    schedule_id: int,
    update_data: TaskScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task schedule."""
    return update_task_schedule(db, schedule_id, current_user.id, update_data)

@router.delete("/{schedule_id}")
def delete_task_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task schedule."""
    return delete_task_schedule(db, schedule_id, current_user.id)