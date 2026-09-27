"""
AI-powered dependency suggestion service using Google Gemini.
Suggests likely task dependencies based on task titles and descriptions,
with confidence scores and reasoning using Google Gemini's native Structured Output API.
All suggestions require human approval.
"""

import json
import logging
import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class DependencySuggestion(BaseModel):
    upstream_task_id: str = Field(description="Exact task ID from the EXISTING TASKS list")
    upstream_task_title: str = Field(description="Title of that upstream task")
    confidence: int = Field(description="Confidence score between 0 and 100")
    reasoning: str = Field(description="One sentence explaining why this task is a necessary prerequisite")


class DependencySuggestionsResponse(BaseModel):
    suggestions: list[DependencySuggestion] = Field(
        default_factory=list,
        description="List of proposed upstream dependencies"
    )


async def suggest_dependencies(
    target_task: dict,
    all_tasks: list[dict],
    existing_deps: list[dict],
) -> dict:
    """
    Use Google Gemini native Structured Output API to suggest dependencies for a target task.

    Args:
        target_task: {id, title, description} of the task to find deps for
        all_tasks: list of {id, title, description, column} for all tasks
        existing_deps: list of {upstream_task_id, downstream_task_id}

    Returns:
        {suggestions: [...], model_used: str, prompt_summary: str}
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("No Gemini API key configured. Returning empty suggestions.")
        return {
            "suggestions": [],
            "model_used": "none",
            "prompt_summary": "AI suggestions unavailable — no API key configured.",
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except ImportError:
        logger.error("google-genai package not installed.")
        return {
            "suggestions": [],
            "model_used": "none",
            "prompt_summary": "google-genai package not installed.",
        }

    model_name = settings.GEMINI_MODEL
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

    prompt = f"""You are a senior software architect and project manager analyzing task dependencies.

EXISTING TASKS IN THE PROJECT:
{task_list_str}

EXISTING DEPENDENCIES (upstream → downstream):
{dep_str}

TARGET TASK TO FIND PREREQUISITES FOR:
  ID: {target_task['id']}
  Title: {target_task['title']}
  Description: {target_task.get('description', 'No description')}

TASK:
Identify which of the EXISTING TASKS must be completed BEFORE the target task can begin.
Only suggest dependencies that make logical technical and operational sense.

CONSTRAINTS:
1. ONLY reference exact IDs from the EXISTING TASKS list above. Do NOT invent IDs.
2. Respect standard software lifecycle: architecture/schema before implementation, backend/API before frontend integration, implementation before integration testing, testing/audits before production deployment.
3. Do NOT suggest dependencies that already exist in the list.
4. If there are no clear prerequisite tasks, return an empty suggestions list.
5. Calibrate confidence scores accurately (0-100). If uncertain, assign lower confidence."""

    # Configure Gemini's native Structured Output JSON API
    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=DependencySuggestionsResponse,
        temperature=0.2,
    )

    max_attempts = 3
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Execute Gemini call in a worker thread to keep the async loop non-blocking
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=prompt,
                config=generation_config,
            )

            raw_text = response.text.strip() if response and response.text else "{}"
            parsed = json.loads(raw_text)
            raw_suggestions = parsed.get("suggestions", [])

            # Deterministic server-side validation against real database IDs
            valid_ids = {t["id"] for t in other_tasks}
            existing_upstream_ids = {
                d["upstream_task_id"]
                for d in existing_deps
                if d["downstream_task_id"] == target_task["id"]
            }

            validated = []
            for s in raw_suggestions:
                uid = s.get("upstream_task_id", "")
                if uid in valid_ids and uid not in existing_upstream_ids:
                    confidence = min(100, max(0, int(s.get("confidence", 0))))
                    if confidence >= 40:  # Noise threshold
                        validated.append({
                            "upstream_task_id": uid,
                            "upstream_task_title": s.get("upstream_task_title", ""),
                            "confidence": confidence,
                            "reasoning": s.get("reasoning", ""),
                        })

            # Sort suggestions by confidence descending
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
            logger.error(f"Failed to parse Gemini structured response as JSON: {e}")
            return {
                "suggestions": [],
                "model_used": model_name,
                "prompt_summary": f"AI response was not valid JSON: {e}",
            }
        except Exception as e:
            last_error = e
            err_str = str(e)
            logger.warning(f"Gemini API attempt {attempt}/{max_attempts} failed: {err_str}")
            if attempt < max_attempts and any(code in err_str for code in ["503", "429", "UNAVAILABLE"]):
                await asyncio.sleep(1.5 * attempt)
                continue
            break

    logger.error(f"Gemini API error after {max_attempts} attempts: {last_error}")
    return {
        "suggestions": [],
        "model_used": model_name,
        "prompt_summary": f"AI service error: {str(last_error)}",
    }
