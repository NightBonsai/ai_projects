<a href="./README.md">🇨🇳 中文</a> | <a href="./README_EN.md">🇺🇸 English</a>


# Amazon Shopping Assistant

## Multi-Agent System + Agentic RAG

Implements a traditional **Retrieval-Augmented Generation (RAG)** pipeline consisting of **Retrieval → Augmentation → Generation**.

Refactors the RAG pipeline into a **Tool** that can be invoked by an LLM through a **ReAct-style Tool Calling Agent** architecture.

```text
LLM is responsible for reasoning.
Tools are responsible for execution.
LangGraph orchestrates the entire workflow.
```

Builds an AI shopping assistant powered by **LangGraph Multi-Agent** architecture and **Agentic RAG**.

```text
Coordinator Agent
        ├── Product QA Agent
        ├── Shopping Cart Agent
        └── Warehouse Manager Agent
```

---



# FastAPI

Provides the backend service and exposes HTTP APIs for frontend applications.

Designed for high performance with asynchronous request handling.

```text
Receive Request
        ↓
Process Business Logic
        ↓
Invoke LLM
        ↓
Return Response
```

---



# Project Structure

## `app.py`

FastAPI application entry point.

Responsibilities:

- Create the FastAPI application
- Register middleware
- Register API endpoints and routers

---

## `agents/`

### `retrieval_generation.py`

Implements the traditional RAG pipeline and integrates **LangSmith** for observability.

**Deprecated**

```text
User Query
    ↓
Streamlit UI
    ↓
POST /rag/
    ↓
rag()                    ← Custom FastAPI endpoint
    ↓
rag_pipeline()           ← Custom RAG pipeline
        │
        ├── Embedding / BM25
        ├── Qdrant Retrieval
        ├── Prompt Construction
        └── OpenAI ChatCompletion
    ↓
Generate Answer
    ↓
rag()
    ↓
Display Response in Streamlit
```

---

### `graph.py`

Builds the LangGraph workflow.

---

### `agents.py`

Defines the workflow nodes for the LangGraph multi-agent system.

---

### `tools.py`

Defines the tools that can be invoked within the LangGraph workflow.

```text
User Query
    ↓
Streamlit UI
    ↓
POST /agent/
    ↓
agent()                     ← Custom FastAPI endpoint
send_feedback()             ← Custom FastAPI endpoint
hitl()                      ← Custom FastAPI endpoint
    ↓
rag_agent_stream_wrapper()  ← Agentic RAG workflow wrapper
        │
        ├── graph.stream()
        ├── LangGraph Workflow
        └── OpenAI ChatCompletion

submit_feedback()           ← User feedback workflow
    ↓
Generate Answer
    ↓
agent()
    ↓
Display Response in Streamlit
```

---

### `prompts/`

Stores all prompt templates used by the system.

```text
prompts
├── coordinator_agent.yaml          # User intent recognition & multi-agent coordination
├── product_qa_agent.yaml           # Product QA agent prompt
├── shopping_cart_agent.yaml        # Shopping cart agent prompt
├── warehouse_manager_agent.yaml    # Warehouse management agent prompt
├── intent_router_agent.yaml        # Intent routing prompt (Deprecated)
└── retrieval_generation.yaml       # Traditional RAG prompt (Deprecated)
```

---

### `utils/`

Utility modules.

```text
utils
├── prompt_management.py    # Prompt management
├── utils.py                # Utility functions
└── ...
```

---

## `api/`

### `endpoints.py`

Defines the actual FastAPI API endpoints.

```text
api_router
├── agent_router
├── feedback_router
└── hitl_router
```

---

### `middleware.py`

Defines middleware executed before requests are processed by FastAPI.

---

### `models.py`

Defines request and response schemas (data models) used for API communication.