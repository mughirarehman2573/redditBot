from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import RedditSchedule, RedditAccount, User
from core.jwt import get_current_user
from schemas.schedule import ScheduleCreate, ScheduleUpdate

router = APIRouter(prefix="/schedule", tags=["schedule"])

@router.post("/{account_id}")
def create_schedule(
    account_id: int,
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = db.query(RedditAccount).filter_by(id=account_id, owner_id=current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    sched = RedditSchedule(
        account_id=account.id,
        run_at=payload.run_at,
        start_date=payload.start_date,
        end_date=payload.end_date,
        action=payload.action,
        prompt=payload.prompt,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


@router.get("/")
def list_schedules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(RedditSchedule)
        .join(RedditAccount)
        .filter(RedditAccount.owner_id == current_user.id)
        .all()
    )


@router.patch("/{schedule_id}")
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sched = (
        db.query(RedditSchedule)
        .join(RedditAccount)
        .filter(RedditSchedule.id == schedule_id, RedditAccount.owner_id == current_user.id)
        .first()
    )

    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sched, key, value)

    db.commit()
    db.refresh(sched)
    return sched

@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sched = (
        db.query(RedditSchedule)
        .join(RedditAccount)
        .filter(RedditSchedule.id == schedule_id, RedditAccount.owner_id == current_user.id)
        .first()
    )

    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(sched)
    db.commit()
    return {"detail": "Schedule deleted successfully"}