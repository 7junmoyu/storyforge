from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import ai, chapters, characters, foreshadows, library, novels, outline, worlds

app = FastAPI(title="StoryForge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(worlds.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(novels.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(outline.router, prefix="/api")
app.include_router(foreshadows.router, prefix="/api")
app.include_router(library.router, prefix="/api")

uploads = Path(__file__).resolve().parents[1] / "data" / "uploads"
uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads), name="uploads")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/settings")
def settings_view() -> dict[str, str | bool]:
    from app.config import settings

    return {
        "ai_configured": bool(settings.ai_api_key.strip()),
        "ai_model": settings.ai_model,
        "ai_base_url": settings.ai_base_url,
    }
