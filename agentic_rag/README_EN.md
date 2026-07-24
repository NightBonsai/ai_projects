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



## Project Structure

### `apps/`

Application source code.

---

### `data/`

Raw datasets and preprocessed data.

After preprocessing, the data is embedded and stored in the **Qdrant** vector database.

---

### `notebooks/`

Project implementation notebooks and experiments.

---

### `env.example`

Example configuration for the `.env` file.

---

### `pyproject.toml` & `uv.lock`

Development environment configuration.

---

### `docker-compose.yml`

Runtime environment configuration for Docker Compose.