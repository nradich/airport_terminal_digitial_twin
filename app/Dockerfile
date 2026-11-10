# Local CPU service; Spark is installed in this reused platform image but never
# imported or started by the App. The query gateway owns compute.
FROM local-uc-spark:0.1.0
RUN uv pip install --system fastapi==0.115.0 uvicorn==0.30.6
WORKDIR /workspace/airport/app
ENV PYTHONPATH=/workspace/airport/src UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000
CMD ["uvicorn", "server.main:app"]
