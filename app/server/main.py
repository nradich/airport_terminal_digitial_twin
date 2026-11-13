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
    return {"ready": True, "mode": "audited_replay"}


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
            "airport_timezone": app.state.data.config.airport_timezone,
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


@app.get("/api/publications/{push_id}/journeys")
def journeys(push_id: str):
    import json

    from airport_twin.tracking import assert_run, run_url

    data = app.state.data
    publication = data.publication(push_id)["audit"]
    results = []
    for row in data.sql.read("journeys", {"push_id": push_id}):
        run = assert_run(data.config, row["run_id"])
        if run.info.status != "FINISHED":
            continue
        inputs = json.loads(row["input_json"])
        if (row["source_run"] != publication["run_id"] or inputs["push_id"] != push_id
                or run.data.tags.get("mlflow.parentRunId") != publication["run_id"]
                or run.data.tags.get("journey.push_id") != push_id):
            raise ReadError("JOURNEY_SOURCE_MISMATCH", status=409)
        results.append(dict(inputs=inputs, profiles=json.loads(row["summary_json"]),
                            run_id=row["run_id"], url=run_url(data.config, row["run_id"])))
    return results


@app.get("/api/publications/{push_id}/assets/{asset_id}/provenance")
def provenance(push_id: str, asset_id: str):
    from airport_twin.provenance import gate_provenance

    return gate_provenance(app.state.data, push_id, asset_id)


@app.get("/api/journeys/{run_id}/durations")
def journey_durations(run_id: str, checkpoint: str, bag: bool, coffee: bool, restroom: bool):
    import json

    from airport_twin.tracking import assert_run

    data = app.state.data
    run = assert_run(data.config, run_id)
    if run.info.status != "FINISHED" or not run.data.tags.get("journey.push_id"):
        raise ReadError("JOURNEY_NOT_FOUND", status=404)
    rows = data.sql.read("journey_durations", dict(
        run_id=run_id, checkpoint=checkpoint, bag=int(bag),
        coffee=int(coffee), restroom=int(restroom),
    ))
    for row in rows:
        if isinstance(row["histogram"], str):
            row["histogram"] = json.loads(row["histogram"])
    return rows


@app.get("/api/publications/{push_id}/frame.png")
def frame(push_id: str):
    return Response(app.state.data.frame(push_id), media_type="image/png")


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "static", html=True),
    name="viewer",
)
