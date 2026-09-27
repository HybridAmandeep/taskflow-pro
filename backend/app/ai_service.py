"""
AI-powered dependency suggestion service using NVIDIA NIM (OpenAI-compatible).
Suggests likely task dependencies based on task titles and descriptions,
with confidence scores and reasoning. All suggestions require human approval.
"""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


async def suggest_dependencies(
    target_task: dict,
    all_tasks: list[dict],
    existing_deps: list[dict],
) -> dict:
    """
    Use NVIDIA NIM to suggest dependencies for a target task.

    Args:
        target_task: {id, title, description} of the task to find deps for
        all_tasks: list of {id, title, description, column} for all tasks
        existing_deps: list of {upstream_task_id, downstream_task_id}

    Returns:
        {suggestions: [...], model_used: str, prompt_summary: str}
    """
    if not settings.NVIDIA_API_KEY:
        logger.warning("No NVIDIA API key configured. Returning empty suggestions.")
        return {
            "suggestions": [],
            "model_used": "none",
            "prompt_summary": "AI suggestions unavailable — no API key configured.",
        }

    client = AsyncOpenAI(
        base_url=settings.NVIDIA_BASE_URL,
        api_key=settings.NVIDIA_API_KEY,
    )

    model_name = settings.NVIDIA_MODEL

    # Build context about existing tasks (excluding the target)
    other_tasks = [t for t in all_tasks if t["id"] != target_task["id"]]
    if not other_tasks:
        return {
            "suggestions": [],
            "model_used": model_name,
            "prompt_summary": "No other tasks to suggest dependencies from.",
        }

    # Format existing task list for the prompt
    task_list_str = ""
    for t in other_tasks:
        task_list_str += (
            f"  - ID: {t['id']}\n"
            f"    Title: {t['title']}\n"
            f"    Description: {t.get('description', 'No description')}\n"
            f"    Status: {t.get('column', 'backlog')}\n\n"
        )

    # Format existing dependencies
    dep_str = ""
    for d in existing_deps:
        dep_str += f"  - {d['upstream_task_id']} → {d['downstream_task_id']}\n"
    if not dep_str:
        dep_str = "  (none yet)\n"

    system_prompt = "You are a senior project manager analyzing task dependencies for a software project. You respond with ONLY valid JSON, no markdown, no commentary."

    user_prompt = f"""EXISTING TASKS IN THE PROJECT:
{task_list_str}

EXISTING DEPENDENCIES (upstream → downstream):
{dep_str}

TARGET TASK (find prerequisites for this task):
  Title: {target_task['title']}
  Description: {target_task.get('description', 'No description')}

YOUR JOB:
Identify which of the EXISTING TASKS should be completed BEFORE the target task can begin.
Only suggest dependencies that make logical sense based on the task titles and descriptions.

RULES:
1. Only reference task IDs from the EXISTING TASKS list above. Do NOT invent task IDs.
2. Consider logical ordering: design before implementation, implementation before testing, setup before integration.
3. Do NOT suggest dependencies that already exist.
4. If you lack sufficient context, set confidence below 40 rather than guessing.
5. If no logical dependencies exist, return an empty suggestions array.

Respond with ONLY valid JSON in this exact format:
{{
  "suggestions": [
    {{
      "upstream_task_id": "<exact task ID from the list>",
      "upstream_task_title": "<title of that task>",
      "confidence": <0-100>,
      "reasoning": "<one sentence explaining why this task should come first>"
    }}
  ]
}}"""

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        raw_text = response.choices[0].message.content.strip()

        # Clean up response — strip markdown fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        # Some models wrap in <think>...</think> tags — strip those
        if "<think>" in raw_text:
            think_end = raw_text.rfind("</think>")
            if think_end != -1:
                raw_text = raw_text[think_end + len("</think>"):].strip()

        parsed = json.loads(raw_text)
        suggestions = parsed.get("suggestions", [])

        # Validate: filter out any suggestions referencing non-existent tasks
        valid_ids = {t["id"] for t in other_tasks}
        existing_upstream_ids = {
            d["upstream_task_id"]
            for d in existing_deps
            if d["downstream_task_id"] == target_task["id"]
        }

        validated = []
        for s in suggestions:
            uid = s.get("upstream_task_id", "")
            if uid in valid_ids and uid not in existing_upstream_ids:
                confidence = min(100, max(0, int(s.get("confidence", 0))))
                if confidence >= 40:  # Filter low-confidence noise
                    validated.append({
                        "upstream_task_id": uid,
                        "upstream_task_title": s.get("upstream_task_title", ""),
                        "confidence": confidence,
                        "reasoning": s.get("reasoning", ""),
                    })

        # Sort by confidence descending
        validated.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "suggestions": validated,
            "model_used": model_name,
            "prompt_summary": (
                f"Analyzed {len(other_tasks)} existing tasks to find "
                f"prerequisites for '{target_task['title']}'. "
                f"Found {len(validated)} suggestions above confidence threshold."
            ),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return {
            "suggestions": [],
            "model_used": model_name,
            "prompt_summary": f"AI response was not valid JSON: {e}",
        }
    except Exception as e:
        logger.error(f"NVIDIA NIM API error: {e}")
        return {
            "suggestions": [],
            "model_used": model_name,
            "prompt_summary": f"AI service error: {str(e)}",
        }
