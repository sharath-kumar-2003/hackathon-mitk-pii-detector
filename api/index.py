"""
Vercel serverless function entry point.
Routes all /api/* requests to the FastAPI application.
"""
import sys
import os

# Ensure the project root is on the path so `backend` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.main import app  # noqa: F401 — Vercel needs the `app` export
