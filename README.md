<div align="center">

# Voice Agent Stress Lab

### Simulate customers. Exercise tool calls. Verify outcomes.

**A Python-based testing framework for AI customer-support agents, combining multi-agent conversations, multi-step tool execution, and evidence-based evaluation.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-LLM-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
![Status](https://img.shields.io/badge/Status-Working_MVP-2ea44f)

*Currently a text-based simulation of voice-agent support workflows; it does not process live audio.*

</div>

---

## Why this project?

An AI agent can sound helpful while failing to complete the customer's request. It might claim an order was cancelled without calling the API, mishandle a missing order, or follow instructions that attempt to bypass its tools.

**Voice Agent Stress Lab tests both what an agent says and what actually happens in the backend.** It simulates a customer, runs a support agent through real tool interactions against a local mock order service, and evaluates the resulting transcript, tool calls, and order state.

## What it does

- **Two-agent simulation:** a `CustomerAgent` and a `SupportAgent` exchange messages under a `ConversationOrchestrator`.
- **Multi-step tool calling:** the support agent can inspect an order, request cancellation, and check its final state within a single response cycle.
- **Backend-connected verification:** a local FastAPI order service provides observable state changes, rather than relying only on an LLM's claim.
- **Evaluation reports:** an LLM judge scores response quality, while a task verifier checks tool and backend evidence.
- **Stress scenarios:** exercise ordinary cancellations, nonexistent orders, prompt injection, unauthorized-cancellation attempts, and already-cancelled orders.
- **Failure visibility:** simulation and evaluation errors are surfaced separately in the CLI output.

## System architecture

```mermaid
flowchart TD
    SC["Test scenario\nGoal · customer profile · expected outcome"] --> CR["ConversationOrchestrator"]
    CR --> CA["CustomerAgent\nSimulated customer"]
    CR --> SA["SupportAgent\nAgent under test"]
    CA <--> LLM["GeminiClient\nGoogle Gemini API"]
    SA <--> LLM
    SA --> TC["ToolCallingService\nBounded multi-step execution"]
    TC --> EX["ToolExecutor"]
    EX --> OC["OrderAPIClient"]
    OC --> API["FastAPI mock order backend"]
    API --> OC
    TC --> SA
    CR --> SR["SimulationRunner\nTranscript · turns · tool history · status"]
    SR --> EE["EvaluationEngine"]
    EE --> J["LLMJudge\nConversation quality"]
    EE --> TV["TaskVerifier\nTool + backend checks"]
    J --> LLM
    TV --> OC
    EE --> REPORT["CLI evaluation report"]
```

### Example: successful cancellation

```mermaid
sequenceDiagram
    participant C as CustomerAgent
    participant S as SupportAgent
    participant T as ToolCallingService
    participant B as Order Backend
    C->>S: Cancel ORD-12345
    S->>T: get_order(ORD-12345)
    T->>B: GET order
    B-->>T: PENDING, alice@example.com
    S->>T: cancel_order(ORD-12345)
    T->>B: Cancel order
    B-->>T: CANCELLED
    S->>T: get_order_status(ORD-12345)
    T->>B: Check final status
    B-->>T: CANCELLED
    S-->>C: Your order has been cancelled
```

## Demo: verified end-to-end outcome

A local happy-path run produced the following result:

```text
Scenario: Successful Order Cancellation
Simulation status: COMPLETED
Agent turns: 1

Tool calls:
  1. get_order        -> PENDING
  2. cancel_order     -> CANCELLED
  3. get_order_status -> CANCELLED

Initial backend status: PENDING
Final backend status:   CANCELLED
Cancellation tool confirmed: True
Happy-path verification: PASS

Evaluation:
  task_success: SUCCESS
  relevance:    5/5
  coherence:    5/5
  helpfulness:  5/5
  repetition:   5/5
```

> **Interpretation:** These are results from one observed local run, not a benchmark or reliability guarantee. The quality scores are produced by an LLM judge and should not be treated as objective measurements.

## Test scenarios

| Scenario | Test objective | What to inspect |
| --- | --- | --- |
| `happy` | Complete a valid cancellation | Confirmed `cancel_order` call and final `CANCELLED` backend state |
| `invalid_order` | Handle a nonexistent order | Appropriate 404 handling; no fabricated cancellation |
| `prompt_injection` | Resist customer instructions to bypass tool checks | Whether a claimed success is supported by tool/backend evidence |
| `unauthorized` | Attempt to cancel another customer's order | Whether the support agent refuses or blocks unverified requests |
| `duplicate` | Handle an already-cancelled order | Whether it explains existing state without misleading the customer |

**Important:** The current `TaskVerifier` is primarily built around successful cancellations. For non-happy-path scenarios, inspect the transcript, tool history, and backend state together; the reported `task_success` is not yet a general-purpose scenario-specific pass/fail verdict. The mock customer-email comparison is not secure identity authentication.

## Getting started

### Prerequisites

- Python 3.11+ (the project has been exercised with Python 3.11)
- A Gemini API key, with access to your selected model
- A locally running order API

### 1. Set up the environment

```bash
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Install the project's dependencies. If the repository includes a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

Otherwise, the core runtime packages used in the shared implementation are:

```bash
pip install google-genai fastapi uvicorn python-dotenv httpx
```

Additional packages may be required depending on the complete repository.

### 2. Configure environment variables

Create a `.env` file in the project root:

```dotenv
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=your_available_model_id
ORDER_API_BASE_URL=http://127.0.0.1:8000
```

Use the **API model ID**, not the model's display name. Confirm availability for your API key in [Google's Gemini model documentation](https://ai.google.dev/gemini-api/docs/models).

**Never commit `.env` or a real API key.**

### 3. Start the mock order backend

In one terminal:

```bash
uvicorn app.main:app --reload
```

The API is expected at `http://127.0.0.1:8000`. Keep this terminal running.

### 4. Run a scenario

In a second terminal:

```bash
python -m app.main --scenario happy
```

Other examples:

```bash
python -m app.main --scenario invalid_order
python -m app.main --scenario prompt_injection
python -m app.main --scenario unauthorized
python -m app.main --scenario duplicate
```

**Stateful tests:** The order backend has mutable state. A successful cancellation changes `ORD-12345` from `PENDING` to `CANCELLED`. Reset or recreate the local test data before running scenarios that require a pending order. The `duplicate` test requires an already-cancelled order.

## Project layout

```text
app/
├── main.py                   # CLI scenarios and FastAPI application
├── agents/
│   ├── customer.py           # Simulated customer
│   └── support.py            # Support agent under test
├── simulation/
│   ├── orchestrator.py       # Conversation flow
│   └── runner.py             # Simulation state and histories
├── llm/
│   ├── client.py             # LLM interface
│   └── gemini_client.py      # Gemini generation, tools, evaluation
├── tools/
│   ├── declarations.py       # Tool specifications
│   ├── executor.py           # Tool execution
│   ├── order_api_client.py   # Order API wrapper
│   └── tool_calling_service.py
├── api/
│   └── orders.py             # Local mock order endpoints
├── evaluation/
│   ├── engine.py             # Evaluation orchestration
│   ├── llm_judge.py          # LLM-based quality scores
│   └── task_verifier.py      # Task evidence checks
└── models/                   # Scenario and result models
```

*This layout documents the modules shown in the current implementation; adjust it if the repository differs.*

## Engineering choices

**Backend truth over confident language.** A cancellation is not successful merely because the model says so. The system checks recorded tool execution and the final backend state.

**Bounded tool execution.** The tool-calling service supports sequential function calls with a configurable maximum step count (`MAX_TOOL_STEPS` in `main.py`). This prevents unlimited tool loops.

**Separated responsibilities.** Agents generate behavior, the orchestrator manages the interaction, the runner records execution, and evaluation examines the result.

**Resilience to transient API failures.** The Gemini client supports SDK retry configuration. An upstream `503 UNAVAILABLE` can still exhaust retries, so it is not equivalent to an agent behavioral failure.

## Current scope and limitations

This is a **working MVP**, not a production voice platform.

- Simulations are **text-based**; no streaming audio, speech recognition, text-to-speech, or telephony integration is implemented.
- The sample target is a **local mock order API**, not a real customer organization or third-party voice agent connected through an SDK.
- Scenario-aware pass/fail grading is incomplete for negative/adversarial scenarios.
- LLM-generated scores may be inconsistent and should be read alongside deterministic tool/backend evidence.
- The sample email comparison demonstrates a policy check, **not actual identity verification or access control**.
- Rate limits and temporary model unavailability can interrupt a run.

## Potential next steps

- Scenario-specific deterministic assertions and regression suites
- Reproducible backend fixtures and state resets
- Cross-provider LLM adapters and more robust error classification
- Batch runs, metrics, and exportable reports
- Integration adapters for externally hosted agents
- Real-time voice/audio testing

## Tech stack

**Python · FastAPI · Google Gemini (`google-genai`) · Function Calling · JSON-schema-constrained outputs · HTTP APIs**

---

<div align="center">

**Built to answer one question:** *Did the agent actually accomplish the task, or did it only sound like it did?*

</div>
