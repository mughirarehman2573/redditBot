import os
import asyncio
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from database.db import engine, Base
from api import auth as auth_routes, reddit as reddit_routes, schedule as schedule_routes, stats as stats_routes
from apscheduler.schedulers.background import BackgroundScheduler
from workers.scheduler import run_schedules
from dotenv import load_dotenv
import logging

load_dotenv()

def create_app() -> FastAPI:
    app = FastAPI(title="RedditBot API (starter)")

    origins = os.getenv("CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://0.0.0.0:8000,http://44.243.107.52:8000"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
        allow_headers=["Authorization","Content-Type","Accept","Origin","X-Requested-With"],
        expose_headers=["Authorization"],
    )

    Base.metadata.create_all(bind=engine)
    app.include_router(auth_routes.router)
    app.include_router(reddit_routes.router)
    app.include_router(schedule_routes.router)

    app.include_router(stats_routes.router)

    @app.get("/config")
    def get_config():
        return JSONResponse({
            "API_BASE": os.getenv("API_BASE", "http://localhost:8000")
        })

    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    scheduler = BackgroundScheduler()

    def run_schedules_wrapper():
        asyncio.run(run_schedules())

    scheduler.add_job(
        run_schedules_wrapper,
        "interval",
        minutes=int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "1"))
    )
    scheduler.start()

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    print("✅ Scheduler started")
    print("⚡ time now", datetime.now())

    return app

app = create_app()
