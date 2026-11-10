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


@app.get("/api/runs/{run_id}/replays")
def replays(run_id: str):
    from airport_twin.app_replay import replay_sets

    return [
        {
            **{k: value for k, value in item.items() if k != "publications"},
            "images": [
                {"step": step, "push_id": p["audit"]["push_id"], "image_type": p["image_type"]}
                for step, p in sorted(item["publications"].items())
            ],
        }
        for item in replay_sets(app.state.data, run_id)
    ]


@app.get("/api/runs/{run_id}/timeline")
def timeline(run_id: str, replay_id: str, start_step: int = 0, end_step: int = 60):
    from airport_twin.app_replay import timeline as read_timeline

    return read_timeline(app.state.data, run_id, replay_id, start_step, end_step)


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
