from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base, get_db
from models import Account, PlannedComment, RunLog
from planner import plan_for_account
from poster import approve_and_post
from email_summary import send_summary

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reddit MVP Now")
templates = Jinja2Templates(directory="templates")

# ---------- Accounts ----------
@app.get("/api/accounts")
def list_accounts(db: Session = Depends(get_db)):
    accs = db.query(Account).all()
    return [{"id": a.id, "label": a.label, "username": a.username, "active_niche": a.active_niche} for a in accs]

@app.post("/api/accounts")
def add_account(
    label: str = Form(...),
    username: str = Form(...),
    refresh_token: str = Form(...),
    client_id: str | None = Form(None),
    client_secret: str | None = Form(None),
    db: Session = Depends(get_db),
):
    acc = Account(
        label=label, username=username, refresh_token=refresh_token,
        client_id=client_id, client_secret=client_secret
    )
    db.add(acc); db.commit(); db.refresh(acc)
    return {"id": acc.id}

@app.post("/api/accounts/{account_id}/niche")
def set_niche(account_id: int, niche: str = Form(...), db: Session = Depends(get_db)):
    acc = db.query(Account).get(account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    acc.active_niche = niche
    db.commit()
    return {"ok": True}

# ---------- Planning / Email ----------
@app.post("/api/plan-run")
def plan_run(account_id: int = Form(...), max_new: int = Form(3), db: Session = Depends(get_db)):
    acc = db.query(Account).get(account_id)
    if not acc:
        raise HTTPException(404, "Account not found")
    n = plan_for_account(db, account_id=account_id, niche_name=acc.active_niche, max_new=int(max_new))
    return {"planned": n}

@app.post("/api/send-summary")
def send_email(limit: int = Form(5), db: Session = Depends(get_db)):
    ok = send_summary(db, limit=limit)
    return {"email_sent": ok}

# ---------- Approvals / Logs ----------
@app.post("/api/approve/{planned_id}")
def approve_post(planned_id: int, db: Session = Depends(get_db)):
    success = approve_and_post(db, planned_id)
    return {"status": "success" if success else "error"}

@app.get("/api/logs")
def logs(db: Session = Depends(get_db)):
    items = db.query(RunLog).order_by(RunLog.id.desc()).limit(100).all()
    return [{"id": x.id, "account_id": x.account_id, "niche": x.niche, "status": x.status, "message": x.message} for x in items]

# ---------- Dashboard ----------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    planned = db.query(PlannedComment).filter_by(posted=False).order_by(PlannedComment.id.desc()).all()
    accounts = db.query(Account).all()
    # basic metrics
    posted_count = db.query(PlannedComment).filter_by(posted=True).count()
    errors = db.query(RunLog).filter_by(status="error").count()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "planned": planned,
        "accounts": accounts,
        "posted_count": posted_count,
        "error_count": errors,
    })
