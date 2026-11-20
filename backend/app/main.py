from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ai, chapters, novels, worlds

app = FastAPI(title="StoryForge", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(worlds.router, prefix="/api")
app.include_router(novels.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
