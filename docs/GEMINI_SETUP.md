# Google Gemini AI Setup Guide — TaskFlow Pro

This guide walks you through configuring, validating, and optimizing the Google Gemini AI features in TaskFlow Pro.

---

## 1. How Gemini Enhances TaskFlow Pro

In modern workflow management, forgotten dependencies often lead to blocked sprints, resource deadlocks, and unplanned delays. 

TaskFlow Pro uses **Google Gemini** (`gemini-3.8-flash`) to intelligently suggest prerequisites when you create or edit a task.

### Key Architectural Guardrails
1. **Context Grounding:** The prompt provides Gemini with only the real tasks already in your database. The model is forbidden from inventing fictional task IDs.
2. **Deterministic Server Validation:** Suggested IDs are cross-checked server-side against actual database records before returning to the frontend.
3. **DAG Cycle Prevention:** Even if accepted by a user, dependencies must pass Kahn's algorithm cycle detection before persistence.
4. **Human-in-the-Loop:** Suggestions are purely advisory. They never auto-apply; the user must click **"Accept"** on each card.
5. **Confidence Scoring:** Every suggestion has an assigned confidence score (0–100%). Suggestions with confidence below 40% are discarded as noise.
6. **Graceful Degradation:** If no API key is provided, the Kanban board, DAG engine, What-If simulator, and critical path visualizer remain 100% functional.

---

## 2. Getting an API Key from Google AI Studio

Google provides free developer access to Gemini models.

1. Navigate to **[Google AI Studio](https://aistudio.google.com/)** (or directly to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
2. Sign in with your standard Google / Gmail account.
3. Click the **"Get API key"** or **"Create API key"** button.
4. In the dialog, select an existing Google Cloud project or choose **"Create API key in new project"**.
5. Copy the generated key:
   - Traditional keys start with `AIzaSy...`
   - Modern keys may start with `AQ...`
   - Both formats are fully supported!

---

## 3. Configuring TaskFlow Pro

### Local Setup
In `backend/.env` (or copy from `.env.example`):

```env
DATABASE_URL=sqlite+aiosqlite:///./taskflow.db
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-3.8-flash
```

### Cloud Setup (Render.com / Railway.app / Docker)
Add the key as an environment variable in your hosting dashboard:
- **`GEMINI_API_KEY`**: `your_actual_key_here`
- **`GEMINI_MODEL`**: `gemini-3.8-flash`

---

## 4. Testing the AI Suggestion Feature

### Running the App
1. Start the backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Open `http://localhost:8000` in your web browser.
3. Click any task card (e.g., *"Write Integration Tests"* or *"Integrate Auth with Frontend"*).
4. Click the **"✨ AI Suggest Dependencies"** button in the modal.
5. You will see suggested prerequisites appear with:
   - Upstream task title
   - Confidence percentage badge (e.g. `90%`)
   - Natural language rationale explaining why this dependency makes sense
   - **Accept** and **Dismiss** action buttons

---

## 5. Troubleshooting & FAQ

| Symptom | Cause | Solution |
|:---|:---|:---|
| *"AI suggestions unavailable — no API key configured"* | `GEMINI_API_KEY` is missing or empty in `.env` | Ensure `.env` exists in `backend/` and contains a valid key, then restart the server. |
| *"google-genai package not installed"* | Python environment is missing the SDK | Run `pip install google-genai==1.14.0` or `pip install -r requirements.txt`. |
| *"models/gemini-2.0-flash is no longer available"* | Deprecated model specified | Set `GEMINI_MODEL=gemini-3.8-flash` in `backend/.env` and restart the server. |
| *"401 / 403 Permission Denied"* | Invalid or expired API key | Generate a fresh key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). |
| *"429 Resource Exhausted"* | Rate limit reached | The free tier allows generous RPM; wait a moment before trying again. |
| API returns an empty list `[]` | Insufficient other tasks or confidence below 40% | Ensure there are other tasks in the project with clear titles and descriptions. |

---

## 6. Related Documentation

- 📖 [Documentation Index](README.md)
- 📡 [REST API Documentation](API_DOCUMENTATION.md)
- 🚀 [Deployment Guide](DEPLOYMENT.md)
- 🏗️ [System Architecture](ARCHITECTURE.md)
