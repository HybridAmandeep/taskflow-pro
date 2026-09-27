# NVIDIA NIM AI Setup Guide — TaskFlow Pro

This guide walks you through setting up and optimizing the NVIDIA NIM AI features in TaskFlow Pro.

---

## 1. How NVIDIA NIM Enhances TaskFlow Pro

> **TL;DR:** NIM analyzes your existing tasks and suggests which ones should be prerequisites for the task you're editing.

TaskFlow Pro uses **NVIDIA NIM** (via the OpenAI-compatible API) to intelligently suggest prerequisites when you create or edit a task. The default model is **DeepSeek R1**, but you can use any model available on the NVIDIA API Catalog.

**Safety by design:**
1. **Context Grounding:** The prompt provides the model with only the real tasks already in your database. The model is forbidden from inventing fictional task IDs.
2. **Confidence Scores:** Each suggestion carries a 0-100 confidence score. Only suggestions ≥ 40% are shown.
3. **Human Approval Required:** Every suggestion must be explicitly accepted or rejected by the user.
4. **DAG Validation:** Accepted suggestions pass through cycle detection before being saved.

---

## 2. Get a Free API Key

NVIDIA provides free developer credits to use NIM models.

1. Visit [build.nvidia.com](https://build.nvidia.com)
2. Click **Login** → sign in with your NVIDIA account (or create one for free)
3. Click on any model (e.g., [DeepSeek R1](https://build.nvidia.com/deepseek-ai/deepseek-r1))
4. Click **"Get API Key"** → Generate a new key
5. Copy the key (starts with `nvapi-`) — **save it immediately**, it's only shown once

---

## 3. Configure TaskFlow Pro

Edit your `backend/.env` file:

```env
NVIDIA_API_KEY=nvapi-your-key-here
NVIDIA_MODEL=deepseek-ai/deepseek-r1
```

### Available Free Models

| Model | ID | Best For |
|-------|----|----------|
| **DeepSeek R1** | `deepseek-ai/deepseek-r1` | Reasoning tasks (default) |
| **DeepSeek V4.1 Flash** | `deepseek-ai/deepseek-v4.1-flash` | Fast, cost-effective |
| **Meta Llama 3.3 70B** | `meta/llama-3.3-70b-instruct` | General purpose |

> **Note:** Model availability changes. Check [build.nvidia.com/models](https://build.nvidia.com/models) and filter by "Free Endpoint" for the latest list.

### Environment Variables

- **Variable Name:** `NVIDIA_API_KEY`
- **Value:** Your API key (starts with `nvapi-`)
- **Variable Name:** `NVIDIA_MODEL`
- **Value:** Model ID from the NVIDIA API Catalog (default: `deepseek-ai/deepseek-r1`)

---

## 4. Verify It Works

1. Restart your server: `python -m uvicorn app.main:app --reload`
2. Open the app in your browser
3. Click on any task → click **"✨ AI Suggest Dependencies"**
4. You should see suggestions with confidence bars (if logical dependencies exist)

---

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| *"AI suggestions unavailable — no API key configured"* | `NVIDIA_API_KEY` is missing or empty in `.env` | Ensure `.env` exists in `backend/` and contains a valid key, then restart the server. |
| *"AI service error: 401"* | Invalid or expired API key | Generate a new key at [build.nvidia.com](https://build.nvidia.com). |
| *"AI service error: 404"* | Model not found or deprecated | Check available models at [build.nvidia.com/models](https://build.nvidia.com/models) and update `NVIDIA_MODEL` in `.env`. |
| *"AI service error: 429"* | Rate limit exceeded | Free tier has ~40 requests/minute. Wait a moment and try again. |
| *Button shows "No suggestions"* | The AI didn't find logical dependencies above the 40% confidence threshold | This is normal for standalone tasks. Try a task with a more descriptive title/description. |
| *Suggestions reference wrong tasks* | This shouldn't happen (server validates IDs) | If it does, check `ai_service.py` logs for the raw response. |

---

## 6. Rate Limits & Fair Use

NVIDIA's free tier provides inference credits with the following approximate limits:

- **~40 requests per minute** (RPM)
- **Credits are refilled periodically**
- **Intended for prototyping and development**

For production use, consider deploying NIM containers on your own GPU infrastructure.
