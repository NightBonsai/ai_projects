# FastAPI

封装后端服务，给前端提供 HTTP  通信接口；高并发，支持异步

接收请求 → 处理逻辑 → 调用大模型 → 返回结果



# Agentic_RAG

实现 检索 Retrieval + 增强 Augmented + 生成 Generation 的固定 Pipeline Chain 流程 

实现 封装 RAG 流程为 Tool 供 Agent 调用的 ReAct-Style Tool Calling Agent 架构 

```
LLM 负责决策，Tool 负责执行，Graph 负责控制整个流程
```



### app.py

FastAPI 入口

- 创建应用
- 注册中间件
- 注册接口 or 路由



### agents/*

retrieval_generation.py:	实现 RAG 固定流程 & 使用 LangSmith 监控 RAG 过程 **(已弃用)**

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

graph.py				    构建 LangGraph Workflow

agents.py				  定义 LangGraph Workflow 节点

tools.py				     定义 LangGraph Workflow 可调用工具

```
用户提问
    ↓
Streamlit UI
    ↓
POST /rag/
    ↓
rag()                    ← 自定义 FastAPI 接口函数
    ↓
rag_agent_wrapper()
    ↓
run_agent()
    ↓
graph.invoke(initial_state)
    ↓
LangGraph Workflow
```

```
LangGraph Workflow
                START
                  │
                  ▼
      intent_router_node
      判断是不是商品问题
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   question_relevant      END
        │
        ▼
    agent_node
 	LLM 思考下一步
        │
        ▼
   tool_router()
        │
   ┌────┴─────────────┐
   │                  │
   ▼                  ▼
ToolNode             END
执行 Tool
   │
   ▼
messages += ToolMessage
   │
   ▼
agent_node
再次思考
   │
   ▼
tool_router()
   │
   ├──需要工具────► 重新循环 ToolNode
   │
   └──回答完成────► END
```

prompts/*				存储 Prompts	

```
prompts	
    ├── intent_router_agent.yaml	# 用户意图识别 Prompt
    ├── qa_agent.yaml				# 主问答 Agent Prompt
    └── retrieval_generation.yaml	# RAG 固定流程脚本使用的 Prompt (已弃用)
```

utils/*					存储功能函数

```
utils		
    ├── prompt_management.py	# 管理 Prompts
    ├── utils.py				# 管理功能函数
    └── ...
```



### api/*

endpoints.py:	定义 FastAPI 调用的真正的接口

```
api_router			# 主接口
    ├── rag_router	# 子接口
    ├── xxx_router
    └── ...
```

middleware.py:     定义中间件（请求进入 FastAPI 前的处理）

models.py:	     定义数据模型/传输用数据结构



