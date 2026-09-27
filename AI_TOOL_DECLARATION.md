# AI Tool Declaration — TaskFlow Pro

## AI/LLM Tools Used in Development

### 1. NVIDIA NIM (DeepSeek R1 via OpenAI-compatible API) — In-Product AI Feature
- **Purpose:** AI-augmented dependency suggestion engine integrated into the application
- **Usage:** When a user requests AI suggestions for task dependencies, the system sends existing task context to NVIDIA NIM and receives structured suggestions with confidence scores and reasoning
- **Human Oversight:** All AI suggestions require explicit user approval. The DAG engine validates accepted suggestions for cycle safety before persistence
- **Hallucination Mitigation:** Context grounding (only existing task IDs valid), structured JSON output, confidence thresholds, server-side validation

### 2. Development Assistance
- **Tool:** Google Antigravity IDE with Claude
- **Usage:** Pair programming assistance during development for code generation, architecture decisions, debugging, and documentation
- **Human Oversight:** All generated code was reviewed, tested, and modified as needed

## How AI Enhances the Solution

The AI integration is **meaningful, not superficial**. It addresses a real project management pain point: forgotten dependencies. When planning tasks, teams frequently overlook prerequisite relationships that later cause sprint delays.

The AI suggestion engine:
1. Analyzes the full context of existing tasks and their relationships
2. Uses chain-of-thought reasoning to identify logical ordering
3. Provides confidence-calibrated suggestions with explanations
4. Maintains human-in-the-loop validation at every step
5. Operates under the authority of the DAG engine for graph correctness

The core dependency engine (cycle detection, schedule propagation, status computation) is **deterministic, algorithmic, and independent of AI** — ensuring correctness regardless of AI availability.
