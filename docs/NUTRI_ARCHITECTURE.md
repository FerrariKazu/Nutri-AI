# Nutri AI: System Architecture & Orchestration

Nutri is a deterministic, science-grounded multi-agent reasoning system. It avoids the "black-box" nature of typical chatbots by using a controlled 13-phase pipeline that separates scientific modeling from linguistic interaction.

## 1. System Philosophy
- **Deterministic Reasoning**: Every recipe and sensory prediction is derived from mechanistic rules (Phase 6) and static sensitivity registries (Phase 11).
- **Epistemic Integrity**: Scientific models of physics and chemistry are privileged. User preferences and historical memory can inform *intent*, but they cannot override physical feasibility.
- **Inspectable Chain-of-Thought**: All internal "thinking" phases are exposed via real-time streaming to the user.

## 2. The 13-Phase Pipeline
Nutri processes every user message through these sequential milestones:

1. **Intent & Constraint Extraction**: Parsing raw text into structured culinary goals.
2. **Domain Feasibility Check**: RAG-based context retrieval to verify ingredient availability.
3. **Culinary / Nutrition Rule Validation**: Initial recipe generation and verification of baseline claims.
4. **Sensory Dimension Modeling**: Predicting texture, flavor, and mouthfeel vectors.
5. **Counterfactual Variant Generation**: Simulating small parameter shifts to check sensitivity.
6. **Trade-off Explanation**: Scientific analysis of competing sensory objectives.
7. **Multi-Objective Optimization**: Solving for the optimal balance of taste and nutrition.
8. **Sensory Pareto Frontier Construction**: Generating a set of non-dominated recipe variations.
9. **Variant Scoring**: Projecting user styles (e.g., "indulgent", "light") onto the frontier.
10. **Constraint Reconciliation**: Enforcing chemical/physical limits on the final choice.
11. **Output Synthesis**: Compiling final culinary instructions.
12. **Explanation Layer**: Adapting feedback for the target audience (Casual to Technical).
13. **Final Structured Response**: Packaging the result for frontend delivery.

## 3. Memory Model
Nutri uses **Session-Scoped SQLite Memory**.
- **Context Only**: History is injected into Phase 1 to inform the "Design Loop" (e.g., remembering that the user wanted more crispness in the previous turn).
- **Stateless Core**: The underlying simulation engines (Phases 5-13) are stateless; they only receive the current snapshot of parameters.
- **Persistence**: Messages are written back to SQLite only after Phase 13 completes successfully.

## 4. API & Streaming Contract

### Request
`POST /nutri/chat`
```json
{
  "session_id": "uuid-string",
  "message": "user input",
  "preferences": {
    "verbosity": "medium",
    "streaming": true
  }
}
```

### Response (SSE)
Chunks are emitted as:
```text
data: {"phase": 8, "title": "Sensory Pareto Frontier", "partial_output": "..."}
```
Final result:
```text
data: {"phase": "final", "output": { "recipe": "...", "explanation": "..." }}
```

## 5. Deployment & Tech Stack
- **Backend**: FastAPI (Python) + SQLite for memory + Ollama (Qwen3) for text transforms.
- **Frontend**: React + Tailwind + Framer Motion (Vercel).
- **Orchestrate**: Custom `NutriOrchestrator` managing the synchronous hand-off between 13 modules.
