# Google Gemini AI Setup Guide — TaskFlow Pro

This guide walks you through setting up and optimizing the Google Gemini AI features in TaskFlow Pro.

---

## 1. How Gemini Enhances TaskFlow Pro

In modern workflow management, forgotten dependencies often lead to blocked sprints and unplanned delays. 

TaskFlow Pro uses **Google Gemini** (`gemini-2.0-flash`) to intelligently suggest prerequisites when you create or edit a task.

### Key Architectural Guardrails
1. **Context Grounding:** The prompt provides Gemini with only the real tasks already in your database. The model is forbidden from inventing fictional task IDs.
2. **Deterministic Validation:** Suggested IDs are checked server-side against the database.
3. **DAG Cycle Prevention:** Even if accepted by a user, dependencies must pass Kahn's algorithm cycle detection before being saved.
4. **Human-in-the-Loop:** Suggestions are purely advisory. They never auto-apply; the user must click **"Accept"** on each card.
5. **Graceful Degradation:** If no API key is provided, the rest of the board functions 100% normally.

---

## 2. Getting an API Key from Google AI Studio

Google provides free developer access to Gemini models.

1. Navigate to **[Google AI Studio](https://aistudio.google.com/)**.
2. Sign in with your standard Google / Gmail account.
3. Click the **"Get API key"** or **"Create API key"** button on the left sidebar.
4. In the dialog, select an existing Google Cloud project or choose **"Create API key in new project"**.
5. Copy the generated key. It will begin with `AIzaSy...`.

---

## 3. Configuring TaskFlow Pro

### Local Setup
Open `backend/.env` in your project folder and add your key:

```env
DATABASE_URL=sqlite+aiosqlite:///./taskflow.db
GEMINI_API_KEY=AIzaSyYourGeneratedKeyHere
GEMINI_MODEL=gemini-2.0-flash
```

### Cloud Setup (Render.com / Railway.app)
Add the key as an environment variable in your hosting dashboard:
- **Variable Name:** `GEMINI_API_KEY`
- **Value:** `AIzaSyYourGeneratedKeyHere`
- **Variable Name:** `GEMINI_MODEL`
- **Value:** `gemini-2.0-flash`

---

## 4. Testing the AI Suggestion Feature

1. Start the backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Open `http://localhost:8000` in your web browser.
3. Click any task card (e.g. *"Write Integration Tests"* or *"Integrate Auth with Frontend"*).
4. Click the **"AI Suggest Dependencies"** button in the modal.
5. You will see suggested prerequisites appear with:
   - Upstream task title
   - Confidence percentage (e.g. 90%)
   - Natural language rationale explaining why this dependency makes sense
   - **Accept** and **Dismiss** action buttons

---

## 5. Troubleshooting

| Symptom | Cause | Solution |
|:---|:---|:---|
| *"AI suggestions unavailable — no API key configured"* | `GEMINI_API_KEY` is missing or empty in `.env` | Ensure `.env` exists in `backend/` and contains a valid key, then restart the server. |
| *"google-genai package not installed"* | Python environment is missing the SDK | Run `pip install google-genai==1.14.0` or `pip install -r requirements.txt`. |
| *"models/gemini-... is not found"* | Unsupported model name specified | Set `GEMINI_MODEL=gemini-2.0-flash` in your `.env`. |
| API returns an empty list `[]` | Insufficient other tasks or confidence below 40% | Ensure there are other tasks on the board to suggest dependencies from. |
