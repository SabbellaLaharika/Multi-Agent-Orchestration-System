from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Multi-Agent AI Orchestration API",
    version="1.0.0",
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

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "multi-agent-orchestrator-api"}
