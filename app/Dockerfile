# Local CPU App service. Spark may exist in the reused platform base image but
# is never imported or started here; the query gateway owns compute.
# Runtime pins live in app/requirements.txt (M7e packaging contract).
FROM local-uc-spark:0.1.0
COPY app/requirements.txt /tmp/airport-app-requirements.txt
RUN uv pip install --system --no-cache -r /tmp/airport-app-requirements.txt
WORKDIR /workspace/airport/app
ENV PYTHONPATH=/workspace/airport/src UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000
CMD ["uvicorn", "server.main:app"]
