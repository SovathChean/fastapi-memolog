"""Application entry point.

This file exists for compatibility with `fastapi dev main.py`.
The actual app is created in app/main.py.
"""

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
