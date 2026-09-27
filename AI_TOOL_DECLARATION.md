# AI Tool Declaration – TaskFlow Pro

Building TaskFlow Pro was a human-led effort. We used AI tools to speed up specific tasks like writing code, spotting bugs, reviewing code, and drafting documentation. AI was an assistant, not the author.

## 1. AI Tools Used During Development

We used Google Antigravity IDE and other AI models for specific development tasks. 

Here is what we used AI for:

* Writing code snippets for specific features.

* Reviewing existing code and suggesting updates.

* Finding bugs, debugging issues, and offering fixes.

* Helping optimize and refactor code.

We designed the architecture, built the features, handled implementation, and managed system integration. Every piece of AI-generated code got a thorough human review and plenty of edits before making it into the codebase.

## 2. Google Gemini for Documentation

We used Google Gemini to help pull the project documentation together. 

We started by writing out all the project details ourselves—its goals, functionality, architecture, tech stack, and implementation steps. Gemini took our raw notes and helped format and organize the final document.

Gemini only handled the presentation, phrasing, formatting, and layout. All the actual technical explanations and project details came straight from us.

## 3. Google Gemini Integration in TaskFlow Pro

TaskFlow Pro actually builds Google Gemini (`gemini-3.8-flash`) right into the app via the `google-genai` SDK to power AI-driven task dependency suggestions.

When a user asks for dependency ideas, the app sends the relevant task data over to Gemini. The model reviews the task list and suggests logical connections.

The backend validates every single suggestion. It filters out bad task IDs, duplicate dependencies, and anything falling below the set confidence threshold.

Users have the final say. They manually accept or dismiss every suggestion. The core scheduling engine relies strictly on deterministic graph algorithms, keeping AI far away from the actual calculations.

## 4. Human Involvement and Verification

Humans drove this project from start to finish. We figured out the requirements, made the technical calls, wired the components together, reviewed the code, and tested the app. 

We also checked all AI-assisted documentation to make sure it matched the reality of our project. 

Ultimately, AI just handled some heavy lifting with coding, debugging, and document formatting. The actual development and every major technical decision stayed firmly in human hands.
