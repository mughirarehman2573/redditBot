from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from database.db import engine, Base
from api import auth as auth_routes, reddit as reddit_routes, schedule as schedule_routes


def create_app() -> FastAPI:
    app = FastAPI(title="RedditBot API (starter)")

    # CORS
    origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "http://44.243.107.52:8000"
    ]
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

    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app

app = create_app()
