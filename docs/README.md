# TaskFlow Pro — Documentation Hub

Welcome to the TaskFlow Pro documentation repository. This directory organizes all technical documentation, architecture specifications, API references, AI integration guides, and deployment workflows for the project.

---

## 📚 Documentation Directory

| Document | Topic | Description |
|:---|:---|:---|
| **[Architecture & Design](ARCHITECTURE.md)** | Core Engineering | Graph theory algorithms (Kahn's, BFS, Critical Path), database models, and system components. |
| **[Testing & Reliability](TESTING_AND_RELIABILITY.md)** | QA & Known Failure Cases | Test suites (22 unit tests, 4 invariant tests) and catalog of 12 known failure cases & mitigations. |
| **[REST API Reference](API_DOCUMENTATION.md)** | Integration & API | Complete endpoint specs, schemas, payloads, error formats, and status codes. |
| **[Deployment Guide](DEPLOYMENT.md)** | DevOps & Hosting | How to host on Render.com, Docker, Railway.app, Fly.io, and Cloudflare tunnels. |
| **[Gemini AI Setup Guide](GEMINI_SETUP.md)** | AI Configuration | Obtaining keys, configuring `gemini-3.8-flash`, guardrails, and troubleshooting. |
| **[AI Tool Declaration](../AI_TOOL_DECLARATION.md)** | Compliance & Ethics | Transparency statement on AI tools used in development and in-product runtime. |
| **[Main README](../README.md)** | Project Overview | Quickstart, feature highlights, seed data, and prerequisites. |

---

## 🧭 System Component Architecture

```
                    +------------------------------------+
                    |        Browser / Client            |
                    |   Vanilla HTML5 / CSS3 / ES6 JS    |
                    | (Kanban Board + Interactive Canvas)|
                    +-----------------+------------------+
                                      |
                             REST API | JSON
                                      v
                    +------------------------------------+
                    |          FastAPI Backend           |
                    |  - Routes: /tasks, /dependencies,  |
                    |            /dag, /ai               |
                    +--------+------------------+--------+
                             |                  |
                             v                  v
                 +-------------------+  +-------------------+
                 |    DAG Engine     |  | Google GenAI SDK  |
                 | (Kahn's / BFS DP) |  | (gemini-3.8-flash)|
                 +---------+---------+  +-------------------+
                           |
                           v
                 +-------------------+
                 | SQLite (aiosqlite)|
                 |    taskflow.db    |
                 +-------------------+
```

---

## 🛠️ Editing and Managing Documentation

When modifying features or adding endpoints, please keep documentation consistent using these standards:

### 1. Document Structure Rules
- **Header:** Start with an H1 title `# Title — TaskFlow Pro` followed by a concise 1–2 sentence description.
- **Table of Contents / Overview:** Include quick summary tables for quick scanning.
- **Code Blocks:** Explicitly specify language tags (`bash`, `json`, `python`, `env`).
- **Cross-Links:** Every document should end with a "Related Documentation" section linking back to the hub.

### 2. Environment Variables Checklist
Whenever changing environment variables (such as AI models or ports), verify all of the following files:
- `.env.example` (Root)
- `backend/.env.example`
- `backend/.env`
- `render.yaml`
- `docs/DEPLOYMENT.md`
- `docs/GEMINI_SETUP.md`
- `README.md`

### 3. Current Version Tokens
- **Gemini Model:** `gemini-3.8-flash`
- **FastAPI Version:** `0.115.0`
- **Python Runtime:** `3.11+`
- **Default Database:** `sqlite+aiosqlite:///./taskflow.db`
