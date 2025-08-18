import smtplib
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
from models import PlannedComment
from settings import settings

def send_summary(db: Session, limit: int = 5):
    if not settings.SMTP_USER or not settings.SMTP_PASS or not settings.EMAIL_TO:
        return False
    planned = db.query(PlannedComment).filter_by(posted=False).order_by(PlannedComment.id.desc()).limit(limit).all()
    if not planned:
        return False
    lines = []
    for p in planned:
        lines.append(f"[{p.subreddit}] {p.post_title}\n{p.post_url}\n— {p.text}\n")
    body = "\n\n".join(lines)
    msg = MIMEText(body)
    msg["Subject"] = f"Reddit planned comments ({len(planned)})"
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.EMAIL_TO
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.sendmail(settings.SMTP_USER, [settings.EMAIL_TO], msg.as_string())
    return True
