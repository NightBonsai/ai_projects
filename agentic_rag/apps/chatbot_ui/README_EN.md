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



# Streamlit

A rapid GUI framework for building AI-powered web applications.

Receives user queries, sends requests to the FastAPI backend, and displays the generated responses.

```text
User Query
    ↓
Streamlit UI
    ↓
FastAPI Backend
    ↓
LLM / Multi-Agent Workflow
    ↓
Response
    ↓
Display in Streamlit
```

---



# Project Structure

## `src/`

Frontend source code.

---

## `pyproject.toml`

Development environment configuration.