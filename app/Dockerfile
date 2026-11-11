# Build dist/app first. No Spark engine or desktop source mounts are required.
FROM python:3.11.14-slim
RUN pip install --no-cache-dir uv==0.10.2
WORKDIR /app
COPY dist/app/ /app/
RUN uv sync --locked --no-dev
ENV PATH=/app/.venv/bin:$PATH UVICORN_PORT=8000
CMD ["python", "launch.py"]
