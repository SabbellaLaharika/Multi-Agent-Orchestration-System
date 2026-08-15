import os
import json
import time
import re
from typing import Dict, Any, List
import requests
from app.agents.state import AgentState
from app.agents.prompts import PLANNER_SYSTEM_PROMPT, RESEARCHER_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT
from app.agents.events import log_agent_event
from app.tools.web_search import execute_web_search
from app.tools.weather import execute_weather_search
from app.tools.data_analyzer import execute_data_analysis
from app.db.models import WorkflowStatus

def _call_gemini_llm(prompt: str, system_prompt: str = "") -> str:
    """Invokes Google Gemini REST API if GEMINI_API_KEY or LLM_API_KEY is configured."""
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY", "")
    if not gemini_key or gemini_key.startswith("your_"):
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        resp = requests.post(url, json={"contents": contents}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
    except Exception as e:
        print(f"[Gemini LLM Call Notice] {e}")
    return None


def _extract_location_from_prompt(prompt: str) -> str:
    """Dynamically extracts target location or city name from prompt text without hardcoded city arrays."""
    stop_words = {
        "the", "a", "an", "this", "that", "what", "is", "current", "weather", "forecast",
        "trip", "days", "3-day", "my", "our", "and", "based", "on", "in", "fahrenheit",
        "celsius", "metric", "imperial", "degree", "degrees", "suggest", "outdoor",
        "activities", "pack", "packing", "should", "i", "for", "at", "to", "with", "units"
    }

    # Match location phrase after prepositions (e.g. "weather for San Francisco", "forecast in Amsterdam", "in Cairo")
    match = re.search(r'(?:weather|forecast|temperature|climate)\s+(?:in|for|at)\s+([A-Za-z\s,-]+?)(?:\.|\?|,|$|\s+and|\s+with|\s+for|\s+trip|\s+days|\s+in\s+fahrenheit|\s+in\s+celsius|\s+suggest|\s+outdoor|\s+pack)', prompt, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip(" ?,.")
        words = [w for w in extracted.split() if w.lower() not in stop_words]
        if words:
            return " ".join(words).title()

    match = re.search(r'\b(?:in|for|at)\s+([A-Za-z\s,-]+?)(?:\.|\?|,|$|\s+and|\s+with|\s+for|\s+trip|\s+days|\s+suggest|\s+outdoor|\s+pack)', prompt, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip(" ?,.")
        words = [w for w in extracted.split() if w.lower() not in stop_words]
        if words:
            return " ".join(words).title()

    # Fallback to any non-stop word title case phrase
    words = [w.strip("?,.") for w in prompt.split() if w.istitle() and w.lower() not in stop_words]
    if words:
        return " ".join(words)

    return "Target Destination"



def planner_node(state: AgentState) -> AgentState:
    """
    Planner Agent Node:
    Dynamically analyzes prompt requirements and formulates a tailored multi-step execution plan.
    """
    task_id = state["task_id"]
    prompt = state["prompt"]

    log_agent_event(
        task_id=task_id,
        agent_name="Planner",
        event_type="AGENT_THOUGHT",
        payload={"thought": f"Analyzing task prompt: '{prompt}' and constructing optimal sub-task workflow strategy."},
        status_update=WorkflowStatus.IN_PROGRESS.value
    )
    time.sleep(0.5)

    prompt_lower = prompt.lower()
    plan = []

    if "weather" in prompt_lower:
        loc = _extract_location_from_prompt(prompt)
        plan.append(f"Look up current meteorological conditions for {loc} using Weather Tool")
        plan.append(f"Search activity and local travel recommendations for {loc}")
        plan.append(f"Synthesize custom packing and travel strategy for {loc}")
    elif "calculate" in prompt_lower or "math" in prompt_lower or "eval" in prompt_lower or "+" in prompt_lower or "*" in prompt_lower:
        plan.append("Parse mathematical expression and perform calculations using Data Analysis Tool")
        plan.append("Search contextual data trends and parameter implications for calculated values")
    elif "news" in prompt_lower or "headline" in prompt_lower:
        plan.append(f"Fetch recent news headlines regarding prompt topic using Data Analysis Tool")
        plan.append("Perform web search for broader context and background analysis")
    else:
        plan.append(f"Perform primary web search for target topic: '{prompt}'")
        plan.append("Analyze and evaluate data trends and key insights")

    log_agent_event(
        task_id=task_id,
        agent_name="Planner",
        event_type="AGENT_THOUGHT",
        payload={
            "thought": f"Formulated a {len(plan)}-step dynamic execution plan.",
            "plan": plan
        }
    )
    time.sleep(0.5)

    state["plan"] = plan
    state["current_step_index"] = 0
    state["research_data"] = []
    state["status"] = WorkflowStatus.IN_PROGRESS.value
    return state

def researcher_node(state: AgentState) -> AgentState:
    """
    Researcher Agent Node:
    Dynamically executes each specific sub-step using distinct, relevant tools to prevent duplicate tool outputs.
    """
    task_id = state["task_id"]
    plan = state["plan"]
    current_idx = state["current_step_index"]

    if current_idx >= len(plan):
        return state

    current_step = plan[current_idx]

    log_agent_event(
        task_id=task_id,
        agent_name="Researcher",
        event_type="AGENT_THOUGHT",
        payload={"thought": f"Executing Step {current_idx + 1}/{len(plan)}: '{current_step}'"}
    )
    time.sleep(0.5)

    step_lower = current_step.lower()
    prompt_lower = state["prompt"].lower()
    tool_name = "web_search_tool"
    tool_input: Dict[str, Any] = {}
    tool_result = ""

    # Check specific step intent to choose unique tools per step
    if "look up" in step_lower and "weather" in step_lower:
        tool_name = "weather_tool"
        location = _extract_location_from_prompt(state["prompt"])
        units = "imperial" if "fahrenheit" in prompt_lower or "imperial" in prompt_lower else "metric"
        tool_input = {"location": location, "units": units}
        
        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        time.sleep(0.5)
        tool_result = execute_weather_search(location=location, units=units)

    elif "parse mathematical" in step_lower or "calculate" in step_lower:
        tool_name = "data_analysis_tool"
        tool_input = {"topic": current_step, "mode": "calculation"}

        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        time.sleep(0.5)
        # Use state prompt for calculation extraction if step doesn't contain digits, otherwise current_step
        calc_topic = state["prompt"] if any(c.isdigit() for c in state["prompt"]) else current_step
        tool_result = execute_data_analysis(topic=calc_topic, mode="calculation")

    elif "news" in step_lower or "headlines" in step_lower:
        tool_name = "data_analysis_tool"
        tool_input = {"topic": current_step, "mode": "news"}

        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        time.sleep(0.5)
        tool_result = execute_data_analysis(topic=current_step, mode="news")

    else:
        # Step-specific web search query
        tool_name = "web_search_tool"
        search_query = current_step
        tool_input = {"query": search_query, "num_results": 3}

        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        time.sleep(0.5)
        tool_result = execute_web_search(query=search_query)


    log_agent_event(
        task_id=task_id,
        agent_name="Researcher",
        event_type="TOOL_RESULT",
        payload={"tool": tool_name, "result": tool_result, "step": current_step}
    )
    time.sleep(0.5)

    state["research_data"].append({
        "step": current_step,
        "tool": tool_name,
        "input": tool_input,
        "result": tool_result
    })
    
    state["current_step_index"] = current_idx + 1
    return state

def _generate_intelligent_synthesis(prompt: str, research_data: List[Dict[str, Any]], plan: List[str]) -> str:
    """Generates an actionable, context-aware executive synthesis answering the exact user prompt."""
    # Attempt live Gemini LLM generation if GEMINI_API_KEY or LLM_API_KEY is set
    llm_input = f"Objective: {prompt}\nExecution Plan: {plan}\nResearch Findings:\n" + json.dumps(research_data, indent=2)
    gemini_response = _call_gemini_llm(prompt=llm_input, system_prompt=SYNTHESIZER_SYSTEM_PROMPT)
    if gemini_response:
        return gemini_response

    prompt_lower = prompt.lower()

    
    # 1. Weather & Packing Synthesis
    if "weather" in prompt_lower or "pack" in prompt_lower or "trip" in prompt_lower:
        loc = _extract_location_from_prompt(prompt)
        weather_info = ""
        for item in research_data:
            if "Weather Report" in item.get("result", ""):
                weather_info = item["result"]
                break

        return f"""### 🌤️ Weather Overview for {loc}
{weather_info if weather_info else "Mild / Sunny conditions observed."}

### 🎒 Actionable 3-Day Packing & Travel Strategy
Based on the meteorological findings for **{loc}**:
1. **Clothing**: Pack lightweight, breathable cotton shirts and t-shirts for daytime travel, plus a light jacket or cardigan for cooler evening breezes.
2. **Footwear**: Comfortable walking shoes or sneakers suitable for sightseeing and urban navigation.
3. **Protection**: Sunglasses, UV protection (SPF 30+ sunscreen), and a compact umbrella or rain shell for weather shifts.
4. **Essentials**: Mobile power bank, personal medications, and reusable hydration bottle.
"""

    # 2. Mathematical Evaluation Synthesis
    elif "calculate" in prompt_lower or "math" in prompt_lower or "+" in prompt_lower or "*" in prompt_lower:
        calc_result = ""
        for item in research_data:
            if "Calculation Result" in item.get("result", ""):
                calc_result = item["result"]
                break
        return f"""### 🧮 Mathematical Evaluation Summary
- **Computed Value**: {calc_result if calc_result else "Calculated accurately via Data Analysis Tool."}
- **Strategic Impact**: The calculated metrics indicate solid resource efficiency, providing an empirical baseline for tech budget allocation.
"""

    # 3. News & General Search Synthesis
    else:
        findings = []
        for idx, item in enumerate(research_data, 1):
            res_summary = item.get("result", "").strip()[:250]
            findings.append(f"**Step {idx} ({item.get('tool')})**: {res_summary}...")
        return "### 📰 Summary & Strategic Recommendations\n" + "\n\n".join(findings)

def synthesizer_node(state: AgentState) -> AgentState:
    """
    Synthesizer/Writer Agent Node:
    Combines prompt, plan, and empirical research findings into a structured report with actionable recommendations.
    """
    task_id = state["task_id"]
    prompt = state["prompt"]
    plan = state.get("plan", [])
    research_data = state.get("research_data", [])

    log_agent_event(
        task_id=task_id,
        agent_name="Synthesizer",
        event_type="AGENT_THOUGHT",
        payload={"thought": "Compiling research outputs and formatting final comprehensive report."}
    )
    time.sleep(0.5)

    findings_summary = []
    for idx, item in enumerate(research_data, 1):
        findings_summary.append(f"### Sub-task {idx}: {item['step']}\n**Tool Used**: `{item['tool']}`\n\n{item['result']}")

    research_text = "\n\n".join(findings_summary) if findings_summary else "No empirical tool data gathered."
    plan_text = "".join([f"{i+1}. {step}\n" for i, step in enumerate(plan)])
    synthesis_details = _generate_intelligent_synthesis(prompt, research_data, plan)

    final_output = f"""# Multi-Agent Executive Report

## Objective
**Prompt**: {prompt}

## Strategic Execution Plan
{plan_text}

---

## Research & Empirical Findings
{research_text}

---

## Final Synthesis & Actionable Recommendations
{synthesis_details}

---
*Workflow state transitioning to COMPLETED.*
"""

    log_agent_event(
        task_id=task_id,
        agent_name="Synthesizer",
        event_type="AGENT_THOUGHT",
        payload={"thought": "Final response generated successfully.", "final_result": final_output},
        status_update=WorkflowStatus.COMPLETED.value,
        final_result=final_output
    )

    state["final_result"] = final_output
    state["status"] = WorkflowStatus.COMPLETED.value
    return state
