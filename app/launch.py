"""Identical local and Apps entry point; no shell expansion is required."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=int(os.getenv("DATABRICKS_APP_PORT", os.getenv("UVICORN_PORT", "8000"))),
    )
