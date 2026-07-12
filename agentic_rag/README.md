# Amazon Shopping Assistant

## Agentic_RAG

实现 检索 Retrieval + 增强 Augmented + 生成 Generation 的固定 Pipeline Chain 流程 

实现 封装 RAG 流程为 Tool 供 Agent 调用的 ReAct-Style Tool Calling Agent 架构 

```
LLM 负责决策，Tool 负责执行，Graph 负责控制整个流程
```

实现 基于 Coordinator + Specialist Agents 多智能体协同 ReAct 架构的 Amazon 网购智能助手

```
Coordinator Agent
        ├── Product QA Agent
        ├── Shopping Cart Agent
        └── Warehouse Manager Agent
```

------



### apps/*

应用源码



### data/*

元数据 & 预处理数据

数据预处理后会存入 Qdrant 向量数据库



### notebook/*

项目实现笔记



### env.example

.env 文件示例



### pyproject.toml & uv.lock

开发环境配置文件



### docker-compose.yml

运行环境配置文件
