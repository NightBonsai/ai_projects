<a href="./README.md">🇨🇳 中文</a> | <a href="./README_EN.md">🇺🇸 English</a>


# ai_projects

## Projects

### ai_project_prototype

AI application prototype based on **Streamlit** and **FastAPI**.

### agentic_rag (Amazon Shopping Assistant)

An AI shopping assistant built with **LangGraph Multi-Agent** architecture and **Agentic RAG**.

---



# Development Environment

- Windows 11
- Python 3.12 / 3.14
- uv package manager
- Cursor IDE

---



# Runtime Environment

- Docker Desktop

If Docker consumes too much disk space, clean unused resources with:

```bash
docker system df

docker image ls
docker ps -a

docker builder prune -a
docker container prune -f
docker image prune -a
```

After cleanup, rebuild the target project:

```bash
uv sync
docker compose up --build
```

---



# Environment Setup

## 1. Install [Python](https://www.python.org/) (3.12 or 3.14)

---

## 2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

---

## 3. Install [Cursor IDE](https://cursor.com/)

---

## 4. Install [Docker Desktop](https://www.docker.com/)

Make sure it is running.

---

## 5. Create the Virtual Environment

Run in the project root directory:

```bash
uv sync
```

---

## 6. Select Python Interpreter

Inside Cursor:

```
Ctrl + Shift + P
```

Choose the project's Python interpreter.

---

## 7. Configure Environment Variables

Create a `.env` file following the format in:

```
.env.example
```

---

## 8. Initialize Qdrant

Initialize the vector database and import product data.

See the notebooks directory for details.

---

## 9. Initialize PostgreSQL

Initialize the relational database and import:

- Shopping Cart
- Product Inventory

See the notebooks directory for details.

---

## 10. Run the Project

From the project root:

First build:

```bash
uv sync
docker compose up --build
```

Subsequent runs:

```bash
docker compose up
```

Open the following services:

| Service          | URL                             |
| ---------------- | ------------------------------- |
| Streamlit        | http://localhost:8501           |
| FastAPI Docs     | http://localhost:8000/docs      |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---



# Features

## 1. Project Prototype

- Streamlit frontend
- FastAPI backend

---

## 2. RAG Pipeline

- Dataset collection & preprocessing
- Deploy Qdrant vector database
- Generate embeddings and index documents
- Implement Retrieval-Augmented Generation (RAG)
- LangSmith observability
- Generate evaluation datasets
- RAG evaluation *(Not implemented)*

```text
ragas (older versions have compatibility issues)
```

- Structured output

```text
Pydantic + Instructor
```

- Hybrid Retrieval

```text
Embedding similarity + BM25 keyword search
```

- Reranking

```text
Cohere
Qwen Rerank
BGE Reranker
```

- Prompt Management

```text
Jinja2
```

---

## 3. Agentic RAG

### Refactor RAG into a ReAct-style Tool Calling Agent

```text
LangGraph

• Intent Recognition
• Query Rewriting
• ReAct-style Tool Calling

The RAG pipeline is exposed as a tool that can be invoked by the agent.
```

![Agentic RAG](./agentic_rag/images/multi-turn-agent-image.png)

### Multi-turn Conversation

```text
PostgreSQL
Store agent checkpoints and conversation history.
```

### Additional Features

- Import product review datasets into Qdrant
- Product Search Tool
- User feedback collection
- MCP Tool integration *(Not implemented)*
- Streaming agent workflow status

```text
Server-Sent Events (SSE)
```

---

## 4. Multi-Agent System

### Shopping Cart Database

```text
PostgreSQL
DBeaver
```

CRUD tools for shopping cart operations.

---

### Multi-Agent Architecture v1

```
Coordinator Agent
├── Product QnA Agent
└── Shopping Cart Agent
```

![Multi-Agent v1](./agentic_rag/images/multi-agents-image-1.0.png)

---

### Warehouse Database

```text
PostgreSQL
DBeaver
```

Inventory management and reservation tools.

---

### Multi-Agent Architecture v2

```
Coordinator Agent
├── Product QnA Agent
├── Shopping Cart Agent
└── Warehouse Manager Agent
```

![Multi-Agent v2](./agentic_rag/images/multi-agents-image-2.0.png)

---

### Planned Features

#### Google Agent Development Kit

*(Optional / Not Implemented)*

Refactor the Warehouse Manager Agent.

#### A2A Protocol

*(Optional / Not Implemented)*

---

## 5. LLMOps

### Multiple LLM Providers

Improve robustness with:

```text
LiteLLM
```

---

### Prompt Caching

```text
LangSmith
```

---

### Human-in-the-Loop

Require user approval before shopping cart operations.

```text
HITL node: Approve / Reject
```

![HITL](./agentic_rag/images/multi-agents-image-3.0.png)

---

### Cloud Deployment *(Not Implemented)*

```text
Qdrant
    ↓
Qdrant Cloud

PostgreSQL
    ↓
Supabase
```