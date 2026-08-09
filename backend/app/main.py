from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.database import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Stateful multi-agent system backend using FastAPI, LangGraph, Celery, Redis, and PostgreSQL",
)

# CORS middleware for React frontend (listening on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        init_db()
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Warning: Database initialization skipped or failed: {e}")

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
