# Clean-checkout build rehearsal: no staged wheel, frontend or desktop environment.
FROM node:22-bookworm-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.2 /uv /uvx /usr/local/bin/
RUN uv python install 3.11.14
WORKDIR /source
COPY . /source/
RUN uv run --python 3.11.14 python scripts/package_app.py --target dev
RUN uv sync --project dist/app --locked --no-dev
RUN cd dist/app && .venv/bin/python -c "import airport_twin; from server.main import app; import importlib.util; assert importlib.util.find_spec('pyspark') is None"
RUN uv sync --project dist/app --locked --no-dev --offline --reinstall
