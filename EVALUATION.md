# System Design & Evaluation Document

## 1. Orchestration Architecture: LangGraph vs. AutoGen

For this system, **LangGraph** was chosen over Microsoft AutoGen.

### Rationale

1. **State Machine vs. Chat Loops**: AutoGen relies heavily on free-form conversational loops between agents. For structured workflows, this can lead to unpredictable loops or missed tool triggers. LangGraph models workflows as explicit state graphs (`StateGraph`), allowing us to define clear execution bounds and conditional transitions (`should_continue`).
2. **Typed State Isolation**: LangGraph allows defining a strict schema (`AgentState` using `TypedDict`). Every node receives the current state, reads the necessary fields, and returns a modified subset. This makes data flow predictable.
3. **Real-time Event Hooking**: In FastAPI + WebSocket applications, capturing exact node transitions, tool invocations, and agent thoughts is straightforward in LangGraph. We intercept state updates at each graph node and broadcast JSON events directly to connected WebSockets and PostgreSQL audit tables.

---

## 2. Agent Roles and System Prompts

The graph consists of three specialized agents connected in sequence: `Planner` -> `Researcher` (loops on tools) -> `Synthesizer`.

### Agent 1: Planner
- **Role**: Takes the initial prompt and breaks it down into a sequential list of 2 to 3 execution sub-steps.
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

### Agent 2: Researcher
- **Role**: Reads the current step from the Planner, selects the appropriate custom tool, and collects data.
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

### Agent 3: Synthesizer
- **Role**: Compiles the original prompt, plan, and all tool execution results into a comprehensive Markdown response.
- **System Prompt**:
```text
You are the Lead Synthesizer Agent.
Your responsibility:
Review the original user prompt, the execution plan created by the Planner, and all empirical research data gathered by the Researcher.
Synthesize these inputs into a polished, comprehensive, and well-structured final answer.

Ensure your response directly answers the user's prompt using clear markdown formatting.
```

---

## 3. Custom Tools & Error Handling

Each tool enforces strict input parameters via **Pydantic** models. Pydantic field descriptions double as instructions for LLM tool invocation.

### Tool 1: `web_search_tool`
- **Pydantic Schema**:
  ```python
  class WebSearchInput(BaseModel):
      query: str = Field(description="The search query string to look up information on the web.")
      num_results: int = Field(default=3, description="Number of search result entries to return (1-10).")
  ```
- **Expected Output**: Bulleted titles, descriptions, and URLs retrieved from Brave Search API.
- **Error Handling**: Wrapped in internal `try/except`. If the external API fails, rate-limits, or lacks an API key, the function returns a formatted fallback search response rather than raising an unhandled exception.

### Tool 2: `weather_tool`
- **Pydantic Schema**:
  ```python
  class WeatherSearchInput(BaseModel):
      location: str = Field(description="The precise city and state/country code, e.g., 'San Francisco, CA', 'Tokyo, JP', or 'London, UK'.")
      units: str = Field(default="metric", description="Temperature measurement units: 'metric' for Celsius or 'imperial' for Fahrenheit.")
  ```
- **Expected Output**: Temperature, feels-like temperature, humidity, wind speed, and weather condition string.
- **Error Handling**: Catches HTTP request failures and invalid location inputs. Returns a clean error diagnostic message back to the agent so it can pivot or report the condition.

### Tool 3: `data_analysis_tool`
- **Pydantic Schema**:
  ```python
  class DataAnalysisInput(BaseModel):
      topic: str = Field(description="The topic, mathematical calculation, or keyword dataset to analyze.")
      mode: str = Field(default="analysis", description="Operational mode: 'analysis' (statistical summary), 'news' (recent headlines), or 'calculation' (arithmetic evaluation).")
  ```
- **Expected Output**: Arithmetic calculation results (evaluating math expressions safely), news headlines from NewsAPI, or dataset summaries.
- **Error Handling**: Math evaluation uses safe character sanitization and exception catching to handle syntax errors gracefully.

---

## 4. State Management Strategy

We manage state across agent nodes using `AgentState`:

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

- `planner_node` writes `plan` and initializes `current_step_index = 0`.
- `researcher_node` reads `plan[current_step_index]`, executes the tool, appends results to `research_data`, and increments `current_step_index`.
- `should_continue` checks `current_step_index < len(plan)`. If true, control routes back to `researcher_node`. Otherwise, control transitions to `synthesizer_node`.

---

## 5. Auditability & Database Logging

All lifecycle events are logged to PostgreSQL via SQLAlchemy:

1. **`task_runs`**: Represents macro task execution (`id`, `prompt`, `status`, `final_result`, `created_at`, `updated_at`).
2. **`agent_events`**: Foreign-keyed to `task_runs.id`. Logs every node thought (`AGENT_THOUGHT`), tool call (`TOOL_INVOCATION`), tool output (`TOOL_RESULT`), and error (`ERROR`).

This separation ensures full auditability—engineers can query any past run to reconstruct exact agent reasoning and tool payloads step by step.
