# Multi-Agent AI Orchestration System - Technical Evaluation & Design Document

## 1. Chosen Orchestration Pattern: LangGraph vs. AutoGen

### Selection Rationale
We selected **LangGraph** as the primary multi-agent orchestration framework for this system.

#### Key Reasons for Selecting LangGraph:
1. **Explicit State Machine Semantics**: Unlike purely conversational frameworks, LangGraph allows modeling agentic workflows as explicit directed graphs (`StateGraph`) with custom TypedDict states (`AgentState`).
2. **Deterministic Control & Conditional Routing**: We define explicit conditional edges (`should_continue`) that evaluate execution state (e.g. comparing `current_step_index` with `len(plan)`). This guarantees strict boundaries so control transitions reliably from the **Planner** to the **Researcher**, loops for necessary tool executions, and advances to the **Synthesizer**.
3. **Fine-Grained Event Interception & Auditability**: LangGraph state updates occur at node boundaries, making it easy to intercept state changes, persist structured audit logs (`AgentEvent`) to PostgreSQL, and stream real-time JSON events via WebSockets to the React UI.

---

## 2. Specialized Agent Roles & System Prompts

The system orchestrates **three distinct AI agents**, each with a dedicated role and system prompt:

### 1. Lead Strategic Planner Agent (`Planner`)
- **Role**: Decomposes complex user queries into an ordered, sequential action plan of 2 to 3 discrete sub-tasks.
- **System Prompt**:
```text
You are the Lead Strategic Planner Agent in a multi-agent orchestration engine.
Your sole responsibility is to analyze the user's input prompt and create a structured, sequential plan of 2 to 3 action steps.
Each step should identify what information needs to be gathered or analyzed.

Rules:
1. Break down complex queries into logical sub-tasks (e.g., Web Search, Weather Check, Data Analysis).
2. Output your plan clearly as discrete executable sub-steps.
3. Be precise, actionable, and concise.
```

### 2. Lead Research Agent (`Researcher`)
- **Role**: Iterates over sub-tasks from the Planner, selects appropriate schema-validated custom tools, and executes them.
- **System Prompt**:
```text
You are the Lead Researcher Agent equipped with specialized custom tools:
1. web_search_tool: Search the web for general information, documentation, and news.
2. weather_tool: Retrieve live weather forecasts and atmospheric conditions.
3. data_analysis_tool: Perform arithmetic calculations, trend analysis, or news extraction.

Your responsibility:
Given the current sub-step from the Planner's strategy, determine which tool to execute, invoke it with valid Pydantic inputs, and collect empirical results.
If a tool encounters an error, adapt gracefully and summarize the findings.
```

### 3. Master Synthesizer Agent (`Synthesizer`)
- **Role**: Aggregates original prompt, initial plan, and gathered tool results to compile a comprehensive final report.
- **System Prompt**:
```text
You are the Lead Synthesizer Agent.
Your responsibility:
Review the original user prompt, the execution plan created by the Planner, and all empirical research data gathered by the Researcher.
Synthesize these inputs into a polished, comprehensive, and well-structured final answer.

Ensure your response directly answers the user's prompt using clear markdown formatting.
```

---

## 3. Custom Tools: Input Schemas, Outputs & Error Handling

All tools utilize **Pydantic** (`BaseModel`, `Field`) for strict input validation and docstrings for LLM tool invocation schema generation. Every tool includes internal `try/except` blocks to prevent external API failures or invalid arguments from crashing the application.

### Tool 1: `web_search_tool`
- **Pydantic Input Schema**:
```python
class WebSearchInput(BaseModel):
    query: str = Field(description="The search query string to look up information on the web.")
    num_results: int = Field(default=3, description="Number of search result entries to return (1-10).")
```
- **Expected Output**: Formatted search result snippets with titles and URLs.
- **Error Handling Strategy**: Catches HTTP/network timeouts or missing API keys (`BRAVE_SEARCH_API_KEY`) and gracefully returns structured fallback contextual search results.

### Tool 2: `weather_tool`
- **Pydantic Input Schema**:
```python
class WeatherSearchInput(BaseModel):
    location: str = Field(description="The precise city and state/country code, e.g., 'San Francisco, CA', 'Tokyo, JP', or 'London, UK'.")
    units: str = Field(default="metric", description="Temperature measurement units: 'metric' for Celsius or 'imperial' for Fahrenheit.")
```
- **Expected Output**: Meteorological metrics including temperature, feels-like temperature, humidity, wind speed, and sky conditions.
- **Error Handling Strategy**: Catches HTTP status errors or missing keys (`OPENWEATHER_API_KEY`) and returns a fallback forecast string with diagnostic details.

### Tool 3: `data_analysis_tool`
- **Pydantic Input Schema**:
```python
class DataAnalysisInput(BaseModel):
    topic: str = Field(description="The topic, mathematical calculation, or keyword dataset to analyze.")
    mode: str = Field(default="analysis", description="Operational mode: 'analysis' (statistical summary), 'news' (recent headlines), or 'calculation' (arithmetic evaluation).")
```
- **Expected Output**: Safely evaluated arithmetic calculation results, NewsAPI headlines, or statistical trend vectors.
- **Error Handling Strategy**: Uses safe `eval` with empty builtins for math evaluation and handles NewsAPI network exceptions gracefully.

---

## 4. State Management Strategy

Workflow state is managed using a shared `AgentState` TypedDict:
```python
class AgentState(TypedDict):
    task_id: str
    prompt: str
    plan: List[str]
    current_step_index: int
    research_data: List[Dict[str, Any]]
    messages: List[BaseMessage]
    final_result: Optional[str]
    status: str
    error: Optional[str]
```
As nodes execute:
1. `planner_node` populates `plan` and sets `current_step_index = 0`.
2. `researcher_node` appends tool results to `research_data` and increments `current_step_index`.
3. `should_continue` conditional edge compares `current_step_index` against `len(plan)` to loop or advance.
4. `synthesizer_node` reads `research_data` and populates `final_result`.

---

## 5. Auditability & Database Logging Strategy

Persisted via asynchronous SQLAlchemy ORM into PostgreSQL:
- **`task_runs`**: Stores macro lifecycle (`id`, `prompt`, `status`, `final_result`, `created_at`, `updated_at`).
- **`agent_events`**: Stores granular micro-events (`id`, `task_run_id`, `agent_name`, `event_type`, `payload`, `timestamp`).
  - Event types: `AGENT_THOUGHT`, `TOOL_INVOCATION`, `TOOL_RESULT`, `COMPLETED`, `ERROR`.
