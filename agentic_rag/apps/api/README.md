# Amazon Shopping Assistant

## Multi-Agents + Agentic_RAG

实现 检索 Retrieval + 增强 Augmented + 生成 Generation 的固定 Pipeline Chain 流程 

实现 封装 RAG 流程为 Tool 供 Agent 调用的 ReAct-Style Tool Calling Agent 架构 

```
LLM 负责决策，Tool 负责执行，Graph 负责控制整个流程
```

实现 基于 LangGraph 多智能体与 Agentic RAG 的 AI 智能购物助手

```
Coordinator Agent
        ├── Product QA Agent
        ├── Shopping Cart Agent
        └── Warehouse Manager Agent
```

------



## FastAPI

封装后端服务，给前端提供 HTTP  通信接口；高并发，支持异步

接收请求 → 处理逻辑 → 调用大模型 → 返回结果

------



### src/*

后端源码



### evals/*

RAG 评估源码



### pyproject.toml

开发环境配置文件
