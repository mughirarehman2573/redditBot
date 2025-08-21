# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.core.config import settings
from backend.app.api.endpoints import auth, reddit_oauth,reddit_accounts,content,niches,tasks,activity, reddit_actions

app = FastAPI(title="Reddit Automation ")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# -------------------------------
# Routers
# -------------------------------
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(reddit_oauth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(reddit_accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(content.router, prefix="/api/v1/content", tags=["content"])
app.include_router(niches.router, prefix="/api/v1/niches", tags=["niches"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["activity"])
app.include_router(reddit_actions.router, prefix="/api/v1/reddit", tags=["reddit-actions"])  # ✅ added

# -------------------------------
# Startup Event
# -------------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# -------------------------------
# Health & Root
# -------------------------------
@app.get("/")
def read_root():
    return {"message": "Reddit Automation API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
