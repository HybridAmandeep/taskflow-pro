# Deployment Guide — TaskFlow Pro

This guide explains how to deploy and host your TaskFlow Pro instance for public, team, or cloud access.

---

## Architecture Overview

TaskFlow Pro is a unified single-service application:
- **Backend:** Python + FastAPI + SQLAlchemy 2.0 (async) + SQLite
- **Frontend:** Vanilla HTML5, CSS3, and modern JavaScript served directly by FastAPI from `backend/static/`
- **AI Engine:** Google Gemini (`gemini-3.8-flash`) via `google-genai`
- **Database:** Self-contained SQLite database (`taskflow.db`) automatically initialized and seeded on first run

Because the frontend is bundled and served directly by FastAPI, you only need to deploy **one single container or web service**.

---

## Deployment Options at a Glance

| Method | Cost | Setup Time | Persistence | Recommended For |
|:---|:---|:---|:---|:---|
| **Render.com** | Free | 3-5 mins | Ephemeral (or Persistent Disk) | Portfolio, demos, free 24/7 web link |
| **Railway.app** | Free trial / Hobby | 3 mins | Persistent Volume supported | Production, teams |
| **Docker / VPS** | $4-5/mo (DigitalOcean/Hetzner) | 10 mins | Full disk persistence | Full control, custom domain |
| **Cloudflare Tunnel** | Free | 1 min | Uses your local machine | Instant live preview / demo |

---

## Option 1: Deploy to Render.com (Recommended & Free)

Render provides free hosting for Python web services with automatic HTTPS and continuous deployment from GitHub.

### Step 1: Push your project to GitHub

```bash
cd taskflow-pro

# Initialize git repository if not already done
git add .
git commit -m "Configure TaskFlow Pro for deployment"

# Push to your GitHub repo
git push -u origin main
```

### Step 2: Create a Web Service on Render

1. Log in to [Render.com](https://render.com/).
2. Click **New +** in the top right and select **Web Service**.
3. Choose **Build and deploy from a Git repository** and click **Next**.
4. Select your `taskflow-pro` repository.
5. Configure the service settings:
   - **Name:** `taskflow-pro` (or any unique name)
   - **Region:** Choose the region closest to you
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan Type:** `Free`

### Step 3: Add Environment Variables

Scroll down to the **Environment Variables** section and add:

| Key | Value | Description |
|:---|:---|:---|
| `GEMINI_API_KEY` | `your_api_key_here` | Your Google AI Studio API key (`AIzaSy...` or `AQ...`) |
| `GEMINI_MODEL` | `gemini-3.8-flash` | The Gemini model identifier |
| `PYTHON_VERSION` | `3.11.9` | Ensures Python 3.11 runtime |

### Step 4: Deploy

Click **Create Web Service**. Render will install dependencies, initialize the database with seed data, and assign a public URL like:
```
https://taskflow-pro-xxxx.onrender.com
```

---

## Option 2: Deploy using Docker

TaskFlow Pro includes a production-ready `Dockerfile` in the root directory.

### Build and Run Locally

```bash
# Build the Docker image
docker build -t taskflow-pro .

# Run the container
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY="your_api_key_here" \
  -e GEMINI_MODEL="gemini-3.8-flash" \
  --name taskflow taskflow-pro
```

Access the app at `http://localhost:8000`.

### Deploying the Docker Container to Fly.io

1. Install Fly CLI: `winget install FiloSottile.flyctl` (or curl on Linux/macOS).
2. Authenticate: `fly auth login`.
3. Launch app:
   ```bash
   fly launch
   ```
4. Set secrets:
   ```bash
   fly secrets set GEMINI_API_KEY="your_key_here" GEMINI_MODEL="gemini-3.8-flash"
   ```
5. Deploy:
   ```bash
   fly deploy
   ```

---

## Option 3: Deploy to Railway.app

1. Go to [Railway.app](https://railway.app/) and sign in with GitHub.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select `taskflow-pro`.
4. In **Settings** → **Build & Start**:
   - **Root Directory:** `/backend`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. In **Variables**, add:
   - `GEMINI_API_KEY`: *Your Gemini API Key*
   - `GEMINI_MODEL`: `gemini-3.8-flash`
6. In **Settings** → **Networking**, click **Generate Domain** to get a public URL (`https://...up.railway.app`).

---

## Option 4: Instant Public Access via Cloudflare Tunnel (No Hosting Required)

If you have TaskFlow Pro running on your machine and want to share it with someone online immediately:

### Using Cloudflare Try (Zero Config):

1. Start your local server:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Open a separate terminal and run:
   ```bash
   npx trycloudflare --port 8000
   ```
3. Cloudflare will print a secure public URL:
   ```
   https://random-assigned-name.trycloudflare.com
   ```

### Using ngrok:

```bash
ngrok http 8000
```

---

## Environment Variables Reference

| Variable | Default Value | Required | Description |
|:---|:---|:---|:---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./taskflow.db` | No | SQLAlchemy database connection string. |
| `GEMINI_API_KEY` | `""` | No | API key from Google AI Studio. AI features are disabled if omitted. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | No | Gemini model identifier (default: `gemini-3.8-flash`). |
| `PORT` | `8000` | No | HTTP port used by cloud providers (automatically set by Render/Railway). |

---

## Troubleshooting

### 1. "No API key configured" on AI Dependency Suggestions
- Verify that `GEMINI_API_KEY` is added to your cloud environment variables.
- Ensure the key begins with `AIzaSy` or `AQ` from [Google AI Studio](https://aistudio.google.com/app/apikey).
- Restart the web service after adding new environment variables.

### 2. Changes reset after server restart (Render Free Tier)
- Render Free Tier spins down after 15 minutes of inactivity and disk writes are ephemeral.
- To persist data permanently across free tier restarts, configure a cloud PostgreSQL database or attach a persistent Render disk.

### 3. Static files or CSS not loading
- Verify that the start command runs with `app.main:app` and that the `static/` directory is located next to `app/` in `backend/`.

---

## Related Documentation

- 📖 [Documentation Index](README.md)
- 📡 [REST API Documentation](API_DOCUMENTATION.md)
- 🤖 [Gemini AI Setup Guide](GEMINI_SETUP.md)
- 🏗️ [System Architecture](ARCHITECTURE.md)
