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
rag_pipeline() ← 自定义 RAG 流程封装函数
	|			 	Embedding/BM25 → Qdrant 检索 → 拼接 prompt → OpenAI ChatCompletion
    ↓
返回 answer
    ↓
rag()
    ↓
Streamlit 显示回复
```

graph.py				    构建 LangGraph Workflow

agents.py				  定义 LangGraph Workflow 节点 (Multi-Agents)

tools.py				     定义 LangGraph Workflow 可调用工具

```
用户提问
    ↓
Streamlit UI
    ↓
POST /agent/
    ↓
agent()						← 自定义 FastAPI 接口函数
send_feedback()				← 自定义 FastAPI 接口函数
hitl()						← 自定义 FastAPI 接口函数
    ↓
rag_agent_stream_wrapper() 	← 自定义 Agentic RAG 流程封装函数
							  	graph.stream()	← 流式输出
							  	LangGraph Workflow
							  	OpenAI ChatCompletion
submit_feedback()			← 自定义 用户反馈提交 流程封装函数
    ↓
生成 answer
    ↓
agent()
    ↓
Streamlit 显示回复
```

prompts/*				存储 Prompts	

```
prompts	
	├── coordinator_agent.yaml			# 用户意图识别 & 多智能体协调 Agent Prompt
    ├── product_qa_agent.yaml			# 商品查询 Agent Prompt
    ├── shopping_cart_agent.yaml		# 购物车操作 Agent Prompt
    ├── warehouse_manager_agent.yaml	# 库存操作 Agent Prompt
    ├── intent_router_agent.yaml		# 用户意图识别节点 Prompt (已弃用)
    └── retrieval_generation.yaml		# RAG 固定流程脚本使用的 Prompt (已弃用)
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
api_router				# 主接口
    ├── agent_router	# 子接口
    ├── feedback_router
    └── hitl_router
```

middleware.py:     定义中间件（请求进入 FastAPI 前的处理）

models.py:	     定义数据模型/传输用数据结构



