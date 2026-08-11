# Multi-Agent AI Orchestration System Implementation Plan

We will build a stateful, auditable multi-agent AI system using **LangGraph**, **FastAPI**, **Celery + Redis**, **PostgreSQL**, and **React**. The system will orchestrate 3 specialized agents (*Planner*, *Researcher*, *Synthesizer*) using custom Pydantic-validated tools, log all steps to Postgres for auditability, and stream real-time progress to the UI via WebSockets.

---

## Key Architectural Choices

> [!IMPORTANT]
> 1. **Framework**: **LangGraph** is used for stateful workflow orchestration with a shared `TypedDict` state.
> 2. **LLM Provider**: Supporting OpenAI, Groq, or direct custom API keys with a resilient mock LLM fallback when API keys are not provided so that the entire system functions out-of-the-box in Docker without requiring external paid keys.
> 3. **Asynchronous Execution**: Celery tasks with Redis message broker offload long-running/IO-heavy tool calls without blocking FastAPI or WebSocket event loops.
> 4. **Audit Logging**: Asynchronous SQLAlchemy storing `task_runs` and `agent_events` in PostgreSQL.

---

## Proposed Implementation Steps

### Step 1: Environment & Project Scaffolding [COMPLETED]
- Establish standard directory hierarchy:
  - `backend/app/{api,core,db,agents,tools,tasks}`
  - `frontend/src/{components,hooks}`
- Create root `.env.example` with config definitions (`DATABASE_URL`, `REDIS_URL`, `LLM_API_KEY`, tool API keys).
- Create `docker-compose.yml` with services: `api`, `ui`, `db` (Postgres 15+), `redis` (Redis 7+), `worker` (Celery).
- Create `Dockerfile` for backend and `Dockerfile` for frontend.
- **Git Commit**: `56142301` - `feat(step-1): setup project foundation with FastAPI backend, React frontend, and Docker configuration`

### Step 2: Database Modeling for Agent Auditability [COMPLETED]
- Configure async & sync SQLAlchemy engine & session factory in `backend/app/db/database.py`.
- Define models in `backend/app/db/models.py`:
  - `TaskRun`: `id` (UUID), `prompt`, `status` (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`), `final_result`, `created_at`, `updated_at`.
  - `AgentEvent`: `id`, `task_run_id` (FK), `agent_name`, `event_type` (`AGENT_THOUGHT`, `TOOL_INVOCATION`, `TOOL_RESULT`, `ERROR`), `payload` (JSON), `timestamp`.
- **Git Commit**: `74e6f3d3` - `feat(step-2): add PostgreSQL logging models, SQLAlchemy DB setup, and Celery Redis task worker`

### Step 3: Celery Task Queue & Custom Tools Implementation [COMPLETED]
- Configure Celery app connected to Redis broker in `backend/app/core/celery_app.py`.
- Define 3 custom tools with Pydantic input schemas and robust `try/except` error handling in `backend/app/tools/`:
  1. `web_search_tool`: Fetches search results (Brave Search API or resilient fallback), schema `WebSearchInput`.
  2. `weather_tool`: Fetches weather data (OpenWeatherMap API or resilient fallback), schema `WeatherSearchInput`.
  3. `data_analysis_tool`: Fetches math evaluation, trend analysis, and news (NewsAPI or resilient fallback), schema `DataAnalysisInput`.
- Create Celery worker task definitions in `backend/app/tasks/tasks.py` decorated with `@celery_app.task`.
- **Git Commit**: `7b896a6` - `feat(step-3): implement custom tools with Pydantic schemas, error handling, and Celery async queueing`

### Step 4: Multi-Agent Orchestration Engine (LangGraph) [COMPLETED]
- Define state schema (`AgentState`) in `backend/app/agents/state.py`.
- Create agent nodes in `backend/app/agents/nodes.py`:
  - `planner_node`: Formulates initial task strategy and sub-steps.
  - `researcher_node`: Determines tool calls, delegates heavy tools to Celery, processes results.
  - `synthesizer_node`: Compiles final user response from gathered research.
- Build state graph with conditional edge routing (`should_continue`) in `backend/app/agents/graph.py`.
- Incorporate streaming callback (`events.py`) to publish real-time events to DB and WebSocket manager.
- **Git Commit**: `6f1ecaa` - `feat(step-4): build LangGraph multi-agent workflow with Planner, Researcher, and Synthesizer nodes`

### Step 5: FastAPI Backend Services (REST & WebSocket Endpoints) [PENDING]
- Initialize FastAPI app with CORS middleware in `backend/app/main.py`.
- REST Endpoint (`backend/app/api/endpoints.py`):
  - `POST /api/tasks` -> Accepts prompt, generates `task_id`, persists initial `TaskRun`, launches background workflow execution, and returns immediately with `{"task_id": "uuid"}`.
  - `GET /api/tasks/{task_id}` -> Fetches task details and logged events.
- WebSocket Endpoint (`backend/app/api/websockets.py`):
  - `WS /api/ws/{task_id}` -> Streams real-time JSON agent events to connected client.
- **Git Commit**: `feat(step-5): add REST and WebSocket API endpoints for task execution and real-time streaming`

### Step 6: React Frontend Application [PENDING]
- Build sleek React application in `frontend/`:
  - `TaskForm`: Input for submitting prompts to `POST /api/tasks`.
  - `useAgentWebSocket`: Custom hook managing WS connection to `/api/ws/{task_id}`.
  - `Timeline`: Renders live trace of agent state changes, thoughts, tool execution status, and final answer.
  - Modern styling with clean glassmorphism UI, status badges, and animated agent step indicators.
- **Git Commit**: `feat(step-6): implement React UI with real-time WebSocket timeline and task submission`

### Step 7: Documentation & Evaluation [PENDING]
- Create `EVALUATION.md`: Details orchestration choices (LangGraph vs AutoGen), agent system prompts, Pydantic tool schemas, error handling, state management.
- Create `README.md`: System overview, setup guide (`docker compose up --build`), architecture flow diagram, example queries.
- **Git Commit**: `docs(step-7): add comprehensive EVALUATION.md and README.md documentation`

---

## Verification Plan

### Automated Verification
- Verify backend imports, SQLAlchemy models, Pydantic schemas, and FastAPI endpoints.
- Test tool execution and error handling.
- Build frontend asset bundle and ensure zero React compile errors.

### Manual / Integration Verification
- Execute system via `docker compose up --build` or local services.
- Submit tasks via `POST /api/tasks`.
- Connect WebSocket client and verify event sequence (`AGENT_THOUGHT` -> `TOOL_INVOCATION` -> `TOOL_RESULT` -> `COMPLETED`).
- Verify Postgres records in `task_runs` and `agent_events`.
