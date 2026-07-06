import numpy as np
from pydantic import BaseModel
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver

from typing import Dict, Any, Annotated, List
from operator import add
import json

from api.agents.agents import agent_node, intent_router_node
from api.agents.agents import ToolCall, RAGUsedContext
from api.agents.tools import get_formatted_items_context, get_formatted_reviews_context
from api.agents.utils.utils import get_tool_descriptions


load_dotenv()
qdrant_client = QdrantClient(url="http://qdrant:6333/")


### State ###
class State(BaseModel):
    messages: Annotated[List[Any], add] = []                # 对话历史: HumanMessage、AIMessage、ToolMessage
    question_relevant: bool = False                         # 问题是否属于商品领域
    iteration: int = 0                                      # 当前 Agent 循环次数
    answer: str = ""                                        # 当前 Agent 生成回答
    available_tools: List[Dict[str, Any]] = []              # Tool 描述
    tool_calls: List[ToolCall] = []                         # LLM 输出的 Tool Call
    final_answer: bool = False                              # 是否结束 or 继续循环生成答案
    references: Annotated[List[RAGUsedContext], add] = []   # 回答引用的商品
    trace_id: str = ""                                      # 一轮对话的 LangSmith Trace ID


### Edges ###
def intent_router_conditional_edges(state: State):
    
    if state.question_relevant:     # 用户问题是否相关
        return "agent_node"
    else:
        return "end"

def tool_router(state: State) -> str:
    """Decide whether to continue or end."""
    
    if state.final_answer:          # 是否为最终回答
        return "end"
    elif state.iteration > 2:       # 是否超过最大循环次数
        return "end"
    elif len(state.tool_calls) > 0: # Agent 请求调用 Tool
        return "tools"
    else:
        return "end"


### Workflow ###
workflow = StateGraph(State)

tools = [get_formatted_items_context, get_formatted_reviews_context]
tool_node = ToolNode(tools)
tool_descriptions = get_tool_descriptions(tools)

workflow.add_node("intent_router_node", intent_router_node)
workflow.add_node("agent_node", agent_node)
workflow.add_node("tool_node", tool_node)

workflow.add_edge(START, "intent_router_node")
workflow.add_conditional_edges(
    "intent_router_node",
    intent_router_conditional_edges,
    {
        "agent_node": "agent_node",
        "end": END
    }    
)
workflow.add_conditional_edges(
    "agent_node",
    tool_router,
    {
        "tools": "tool_node",
        "end": END
    }    
)
workflow.add_edge("tool_node", "agent_node")


### Agent Execution Function ###
# 流式输出
def rag_agent_stream_wrapper(question: str, thread_id: str):

    def _string_for_sse(message: str):
        return f"data: {message}\n\n"

    def _process_graph_event(chunk):

        def _is_node_start(chunk):
            return chunk[1].get("type") == "task"

        def _is_node_end(chunk):
            return chunk[0] == "updates"

        def _tool_to_text(tool_call):
            if tool_call.name == "get_formatted_items_context":
                return f"Looking for items: {tool_call.arguments.get("query", " ")}."
            elif tool_call.name == "get_formatted_reviews_context":
                return f"Fetching user reviews..."
            else:
                return f"Unknown tool: {tool_call.name}."

        if _is_node_start(chunk):
            if chunk[1].get("payload", {}).get("name") == "intent_router_node":
                return "Analysing the question..."
            if chunk[1].get("payload", {}).get("name") == "agent_node":
                return "Planning..."
            if chunk[1].get("payload", {}).get("name") == "tool_node":
                message = " ".join([_tool_to_text(tool_call) for tool_call in chunk[1].get("payload", {}).get("input", {}).tool_calls])
                return message
        else:
            return False
    
    # 图状态初始化
    initial_state = {
        "messages": [{"role": "user", "content": question}],
        "iteration": 0,
        "available_tools": tool_descriptions
    }

    # 多轮对话: 设置 & 多轮对话
    config = {                      
        "configurable": {
            "thread_id": thread_id
        }
    }
    with PostgresSaver.from_conn_string("postgresql://langgraph_user:langgraph_password@postgres:5432/langgraph_db") as checkpointer:
        # 流式输出
        graph = workflow.compile(checkpointer=checkpointer)
        for chunk in graph.stream(
            initial_state, 
            config=config,
            stream_mode=["debug", "values"]
        ): 
            processed_chunk = _process_graph_event(chunk)
            if processed_chunk:
                yield _string_for_sse(processed_chunk)

            if chunk[0] == "values":
                result = chunk[1]
    
    # 通过 LLM 查询得到的商品 ID ，再一次去数据库查详细信息
    # -- 第一次数据库查询: Embedding Similarity
    # -- 第二次数据库查询: 通过已获得的 parent_asin 商品 ID 回数据库检索详细信息
    used_context = []                                       # 存储检索数据
    dummy_vector = np.zeros(1536).tolist()
    for item in result.get("references", []):
        payload = qdrant_client.query_points(               # 向量数据库检索
            collection_name="Amazon-items-collection-01-hybrid-search",
            query=dummy_vector,
            limit=1,
            using="text-embedding-3-small",
            with_payload=True,
            query_filter=Filter(                            # 检索条件
                must=[
                    FieldCondition(
                        key="parent_asin",                  
                        match=MatchValue(value=item.id)
                    )
                ]
            )
        ).points[0].payload

        image_url = payload.get("image")                    # 检索结果
        price = payload.get("price")
        if image_url:
            used_context.append({
                "image_url": image_url,
                "price": price,
                "description": item.description
            })
    
    yield _string_for_sse(json.dumps(
        {
            "type": "final_result",
            "data": {
                "answer": result.get("answer", ""),
                "used_context": used_context,
                "trace_id": result.get("trace_id", "")
            }
        }
    ))

# 非流式输出 (已弃用)
# def run_agent(question: str, thread_id: str) -> dict:
    
#     initial_state = {
#         "messages": [{"role": "user", "content": question}],
#         "iteration": 0,
#         "available_tools": tool_descriptions
#     }

#     # 多轮对话设置
#     config = {                      
#         "configurable": {
#             "thread_id": thread_id
#         }
#     }

#     # 多轮对话
#     with PostgresSaver.from_conn_string("postgresql://langgraph_user:langgraph_password@postgres:5432/langgraph_db") as checkpointer:
#         graph = workflow.compile(checkpointer=checkpointer)
#         result = graph.invoke(initial_state, config)

#     return result

# 非流式输出 (已弃用)
# def rag_agent_wrapper(question, thread_id):
    
#     result = run_agent(question, thread_id)
    
#     # 通过 LLM 查询得到的商品 ID ，再一次去数据库查详细信息
#     # -- 第一次数据库查询: Embedding Similarity
#     # -- 第二次数据库查询: 通过已获得的 parent_asin 商品 ID 回数据库检索详细信息
#     used_context = []                                       # 存储检索数据
#     dummy_vector = np.zeros(1536).tolist()
#     for item in result.get("references", []):
#         payload = qdrant_client.query_points(               # 向量数据库检索
#             collection_name="Amazon-items-collection-01-hybrid-search",
#             query=dummy_vector,
#             limit=1,
#             using="text-embedding-3-small",
#             with_payload=True,
#             query_filter=Filter(                            # 检索条件
#                 must=[
#                     FieldCondition(
#                         key="parent_asin",                  
#                         match=MatchValue(value=item.id)
#                     )
#                 ]
#             )
#         ).points[0].payload

#         image_url = payload.get("image")                    # 检索结果
#         price = payload.get("price")
#         if image_url:
#             used_context.append({
#                 "image_url": image_url,
#                 "price": price,
#                 "description": item.description
#             })
    
#     return {
#         "answer": result.get("answer", ""),
#         "used_context": used_context,
#         "trace_id": result.get("trace_id", "")
#     }


