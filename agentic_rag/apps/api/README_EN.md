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



## Project Structure

### `src/`

Backend source code.

---

### `evals/`

Source code for RAG evaluation.

---

### `pyproject.toml`

Development environment configuration.