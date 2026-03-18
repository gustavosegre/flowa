from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from flowa.api.routes.pipelines import router as pipelines_router
from flowa.api.routes.runs import router as runs_router
from flowa.database.db import init_db

UI_STATIC = Path(__file__).parent.parent / "ui" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Flowa",
    description="Mini Airflow — pipeline orchestration API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(pipelines_router)
app.include_router(runs_router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")


app.mount("/ui", StaticFiles(directory=str(UI_STATIC), html=True), name="ui")
