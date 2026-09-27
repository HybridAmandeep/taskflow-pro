# AI Tool Declaration – TaskFlow Pro

## 1. AI Integration: Google Gemini

TaskFlow Pro runs on Google Gemini (`gemini-3.8-flash`) via the official `google-genai` SDK. It powers our intelligent task dependency suggestions. The AI reads your project data to figure out how tasks relate to each other and suggests prerequisites on the fly.

### How It Works

Hit the AI Suggest Dependencies button. The app gathers your task titles, descriptions, statuses, and current links, then fires that data off to Google Gemini with clear instructions. 

Gemini processes the request and sends back suggested dependencies as JSON, complete with confidence scores and short explanations. 

The backend handles the heavy lifting next. It checks the suggestions against the database, strips out duplicates, and drops anything scoring below 40% confidence. 

Nothing happens automatically. You review every single suggestion, choosing what to accept and what to ignore. Once you accept a dependency, the app runs Kahn's algorithm to catch any loops and keep the Directed Acyclic Graph (DAG) intact.

### Safety and Validation

Bad AI suggestions are frustrating. We built safeguards to stop them:

* Strict grounding: Gemini only uses real task data and valid task IDs.
* Backend validation: Fake IDs and duplicate links get instantly tossed.
* Cycle detection: Graph algorithms block circular dependencies before they break things.
* Confidence filtering: Anything under 40% confidence gets thrown away.
* Human approval: You have the final say on every single link.
* Independent operation: If the Gemini API goes down, the core app and scheduler keep right on running.

## 2. AI Tools Used During Development

We built TaskFlow Pro with help from Google Antigravity IDE and advanced Large Language Models (LLMs). 

They carried a lot of weight during code generation, architecture planning, debugging, refactoring, writing docs, and testing.

Here is where the AI stepped in:

* Scaffolding the initial FastAPI backend and SQLAlchemy 2.0 async database models.
* Writing graph algorithms for cycle detection, schedule propagation, and critical path calculations.
* Designing responsive user interfaces alongside an interactive HTML5 Canvas visualizer.
* Drafting automated tests, API documentation, deployment configs, and environment files.

### Human Verification

AI code is never pushed blindly. A human developer reviewed, edited, and tested every line before it made it into the project.

We use an automated test suite in `app/tests/test_dag_engine.py` to double-check the math and logic behind our graph algorithms.

Once the app is running, the core scheduling engine doesn't rely on AI at all. It uses purely deterministic code—topological sorting, Breadth-First Search (BFS), and Dynamic Programming.

## 3. AI Governance and Data Privacy

TaskFlow Pro sticks to a strict human-in-the-loop model. AI suggestions never alter your project structure without your direct sign-off.

We keep the AI on a tight leash using structured prompts, JSON parsing, database checks, confidence cutoffs, and graph-based cycle detection. 

Your task data only goes to Google Gemini when you actively click to get suggestions. We make sure credentials and secrets never get sent to the API.

The scheduling engine and the AI suggestion feature are completely decoupled. If Gemini drops offline or errors out, you can still manage tasks, build dependencies, and run schedules without missing a beat.

## 4. Summary

AI pulls double duty in TaskFlow Pro. It gives users smart dependency suggestions, and it helped developers build the app faster in the first place.

Google Gemini handles optional recommendations. Meanwhile, rock-solid, deterministic graph algorithms take care of the actual scheduling, validation, and critical path math.

You stay in the driver's seat. Every AI suggestion waits for your green light before changing a single thing in your project workflow.
