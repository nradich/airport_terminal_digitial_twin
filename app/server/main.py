"""Thin FastAPI presentation layer; business reads stay in airport_twin."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from airport_twin.app_data import TwinData
from airport_twin.config import Config
from airport_twin.readers import (
    DatabricksSqlReader,
    DatabricksVolumeReader,
    LocalSqlReader,
    LocalVolumeReader,
    ReadError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Config.from_env()
    sql = LocalSqlReader() if config.platform == "local" else DatabricksSqlReader(config)
    volume = (
        LocalVolumeReader(config) if config.platform == "local" else DatabricksVolumeReader(config)
    )
    app.state.data = TwinData(config, sql, volume)
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(ReadError)
async def read_error(_request, error: ReadError):
    return JSONResponse(
        status_code=error.status, content={"error": error.code, "message": str(error)}
    )


@app.get("/api/health")
def health():
    return {"ready": True, "mode": "current"}


@app.get("/api/runs")
def runs():
    return app.state.data.runs()


@app.get("/api/runs/{run_id}/current")
def current(run_id: str):
    return app.state.data.current(run_id)


@app.get("/api/publications/{push_id}")
def publication(push_id: str):
    return app.state.data.publication(push_id)


@app.get("/api/publications/{push_id}/model.glb")
def model(push_id: str):
    return Response(app.state.data.model(push_id), media_type="model/gltf-binary")


@app.get("/api/publications/{push_id}/frame.png")
def frame(push_id: str):
    return Response(app.state.data.frame(push_id), media_type="image/png")


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "static", html=True),
    name="viewer",
)
