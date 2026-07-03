"""
Legacy entrypoint — redirects to new FastAPI backend.

Run the v2 stack instead:
  .\\scripts\\dev.ps1          # API on :8000
  cd frontend && npm run dev   # UI on :3000
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir="backend",
    )
