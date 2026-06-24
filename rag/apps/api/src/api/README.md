# FastAPI

封装后端服务，给前端提供 HTTP  通信接口；高并发，支持异步

接收请求 → 处理逻辑 → 调用大模型 → 返回结果



# RAG

实现 检索 Retrieval + 增强 Augmented + 生成 Generation 流程      



### app.py

FastAPI 入口

- 创建应用
- 注册中间件
- 注册接口 or 路由



### agents/retrieval_generation.py

实现 RAG 核心功能

使用 LangSmith 监控 RAG 过程

```
用户提问
    ↓
Streamlit UI
    ↓
POST /rag/
    ↓
rag()          ← 自定义 FastAPI 接口函数
    ↓
rag_pipeline() ← 用户提问变 Embedding → 去向量数据库检索相似资料 → 资料作为 prompt 塞给 LLM → LLM基于资料回答
    ↓
retrieve_data()
    ↓
Qdrant
    ↓
OpenAI
    ↓
生成回复
    ↓
返回给 rag()
    ↓
返回 JSON
    ↓
Streamlit 显示回复
```



### api/*

endpoints.py:	定义真正的接口

```
api_router			# 主接口
    ├── rag_router	# 子接口
    ├── xxx_router
    └── ...
```

middleware.py:     定义中间件（请求进入 FastAPI 前的处理）

models.py:	     定义数据模型/传输用数据结构
