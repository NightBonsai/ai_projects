import numpy as np
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver

from typing import Dict, Any, Annotated, List
from operator import add
import json

from langsmith import traceable
from langgraph.types import Command, interrupt
from langchain_core.messages import AIMessage
from typing import Literal

from api.agents.agents import coordinator_agent, product_qa_agent, shopping_cart_agent, warehouse_manager_agent
from api.agents.agents import ToolCall, Delegation, RAGUsedContext
from api.agents.tools import (
    get_formatted_items_context, get_formatted_reviews_context, 
    add_to_shopping_cart, remove_from_cart, get_shopping_cart, 
    check_warehouse_availability, reserve_warehouse_items
)
from api.agents.utils.utils import get_tool_descriptions


load_dotenv()
qdrant_client = QdrantClient(url="http://qdrant:6333/")


### State ###
class CoordinatorAgentProperties(BaseModel):
    iteration: int = 0
    final_answer: bool = False
    plan: List[Delegation] = []
    next_agent: str = ""

class AgentProperties(BaseModel):
    iteration: int = 0                                      # 当前 Agent 循环次数
    available_tools: List[Dict[str, Any]] = []              # Tool 描述
    tool_calls: List[ToolCall] = []                         # LLM 输出的 Tool Call
    final_answer: bool = False                              # 是否结束 or 继续循环生成答案

class State(BaseModel):
    messages: Annotated[List[Any], add_messages] = []                                           # 对话历史: HumanMessage、AIMessage、ToolMessage
    user_intent: str = ""                                                                       # 用户意图: 问题是否属于商品领域
    coordinator_agent: CoordinatorAgentProperties = Field(default_factory=AgentProperties)
    product_qa_agent: AgentProperties = Field(default_factory=AgentProperties)
    shopping_cart_agent: AgentProperties = Field(default_factory=AgentProperties)
    warehouse_manager_agent: AgentProperties = Field(default_factory=AgentProperties)
    answer: str = ""                                                                            # 当前 Agent 生成回答
    references: Annotated[List[RAGUsedContext], add] = []                                       # 回答引用的商品
    user_id: str = ""
    cart_id: str = ""
    trace_id: str = ""                                      # 一轮对话的 LangSmith Trace ID


### HITL Node ###
# Human In The Loop: 用户确认是否需要将物品添加进购物车
@traceable(
    name="hitl_add_to_cart"
)
def hitl_add_to_cart(state) -> Command[Literal["shopping_cart_agent_tool_node", END]]:
    
    for tool_call in state.shopping_cart_agent.tool_calls:
        if tool_call.name == "add_to_shopping_cart":
            items_to_add = tool_call.arguments["items"]
            break

    human_input = interrupt({"items_to_add": items_to_add}) # 获取前端用户确认
    if human_input.get("confirmed"):    # 确认添加
        return Command(
            update={},
            goto="shopping_cart_agent_tool_node"    # 执行 tool
        )
    else:                               # 确认不添加
        last_msg = state.messages[-1]
        sanitized = AIMessage(
            content=last_msg.content,
            id=last_msg.id,     # same id = replace instead of append
        )

        return Command(
            update={
                "messages": [sanitized],
                "answer": "You have rejected the addition of items to the cart."
            }, 
            goto=END                                # 路由到 END
        )


### Edges ###
def coordinator_agent_edge(state):
    
    if state.coordinator_agent.final_answer and len(state.coordinator_agent.plan) == 0:   # 是否为最终回答
        return "end"
    elif state.coordinator_agent.iteration> 3:                              # 是否超过最大循环次数
        return "end"
    elif state.coordinator_agent.next_agent == "product_qa_agent":          # 用户需要商品信息检索 product_qa_agent
        return "product_qa_agent"
    elif state.coordinator_agent.next_agent == "shopping_cart_agent":       # 用户需要购物车增删改 shopping_cart_agent
        return "shopping_cart_agent"
    elif state.coordinator_agent.next_agent == "warehouse_manager_agent":   # 用户需要查询 or 预留库存 warehouse_manager_agent
        return "warehouse_manager_agent"
    else:
        return "end"

def product_qa_agent_tool_edge(state) -> str:
    """Decide whether to continue or end."""
    
    if state.product_qa_agent.final_answer:             # 是否为最终回答
        return "end"
    elif state.product_qa_agent.iteration > 4:          # 是否超过最大循环次数
        return "end"
    elif len(state.product_qa_agent.tool_calls) > 0:    # Agent 请求调用 Tool
        return "tools"
    else:
        return "end"

def shopping_cart_agent_tool_edge(state) -> str:
    """Decide whether to continue or end."""
    
    add_to_cart_tool_call = False
    for tool_call in state.shopping_cart_agent.tool_calls:
        if tool_call.name == "add_to_shopping_cart":    # 若有调用 shopping cart agent 
            add_to_cart_tool_call = True                # 启用 Human in the loop
        break

    if state.shopping_cart_agent.final_answer:          # 是否为最终回答
        return "end"
    elif state.shopping_cart_agent.iteration > 2:       # 是否超过最大循环次数
        return "end"
    elif len(state.shopping_cart_agent.tool_calls) > 0: # Agent 请求调用 Tool
        if add_to_cart_tool_call:
            return "hitl_add_to_cart"                   # 进入 Human in the loop
        else:
            return "tools"
    else:
        return "end"

def warehouse_manager_agent_tool_edge(state) -> str:
    """Decide whether to continue or end."""
    
    if state.warehouse_manager_agent.final_answer:          # 是否为最终回答
        return "end"
    elif state.warehouse_manager_agent.iteration > 2:       # 是否超过最大循环次数
        return "end"
    elif len(state.warehouse_manager_agent.tool_calls) > 0: # Agent 请求调用 Tool
        return "tools"
    else:
        return "end"


### Workflow ###
workflow = StateGraph(State)

product_qa_agent_tools = [get_formatted_items_context, get_formatted_reviews_context]
product_qa_agent_tool_node = ToolNode(product_qa_agent_tools)
product_qa_agent_tool_descriptions = get_tool_descriptions(product_qa_agent_tools)

shopping_cart_agent_tools = [add_to_shopping_cart, remove_from_cart, get_shopping_cart]
shopping_cart_agent_tool_node = ToolNode(shopping_cart_agent_tools)
shopping_cart_agent_tool_descriptions = get_tool_descriptions(shopping_cart_agent_tools)

warehouse_manager_agent_tools = [check_warehouse_availability, reserve_warehouse_items]
warehouse_manager_agent_tool_node = ToolNode(warehouse_manager_agent_tools)
warehouse_manager_agent_tool_descriptions = get_tool_descriptions(warehouse_manager_agent_tools)

workflow.add_node("coordinator_agent", coordinator_agent)
workflow.add_node("product_qa_agent", product_qa_agent)
workflow.add_node("shopping_cart_agent", shopping_cart_agent)
workflow.add_node("warehouse_manager_agent", warehouse_manager_agent)
workflow.add_node("hitl_add_to_cart", hitl_add_to_cart)     # Human In The Loop

workflow.add_node("product_qa_agent_tool_node", product_qa_agent_tool_node)
workflow.add_node("shopping_cart_agent_tool_node", shopping_cart_agent_tool_node)
workflow.add_node("warehouse_manager_agent_tool_node", warehouse_manager_agent_tool_node)

workflow.add_edge(START, "coordinator_agent")
workflow.add_conditional_edges(
    "coordinator_agent",
    coordinator_agent_edge,
    {
        "product_qa_agent": "product_qa_agent",
        "shopping_cart_agent": "shopping_cart_agent",
        "warehouse_manager_agent": "warehouse_manager_agent",
        "end": END
    }    
)
workflow.add_conditional_edges(
    "product_qa_agent",
    product_qa_agent_tool_edge,
    {
        "tools": "product_qa_agent_tool_node",
        "end": "coordinator_agent"
    }    
)
workflow.add_conditional_edges(
    "shopping_cart_agent",
    shopping_cart_agent_tool_edge,
    {
        "tools": "shopping_cart_agent_tool_node",
        "hitl_add_to_cart": "hitl_add_to_cart",
        "end": "coordinator_agent"
    }    
)
workflow.add_conditional_edges(
    "warehouse_manager_agent",
    warehouse_manager_agent_tool_edge,
    {
        "tools": "warehouse_manager_agent_tool_node",
        "end": "coordinator_agent"
    }    
)
workflow.add_edge("product_qa_agent_tool_node", "product_qa_agent")
workflow.add_edge("shopping_cart_agent_tool_node", "shopping_cart_agent")
workflow.add_edge("warehouse_manager_agent_tool_node", "warehouse_manager_agent")

graph = workflow.compile()


### Agent Execution Function ###
# 流式输出
def rag_agent_stream_wrapper(question, thread_id: str, mode: str):

    def _string_for_sse(message: str):
        return f"data: {message}\n\n"

    def _process_graph_event(chunk):

        def _is_interrupt(chunk):
            return len(chunk[1].get('payload', {}).get('interrupts', [])) > 0

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
            if chunk[1].get("payload", {}).get("name") == "coordinator_agent":
                return"Planning..."
            if chunk[1].get("payload", {}).get("name") == "product_qa_agent":
                return "Fetching information about inventory..."
            if chunk[1].get("payload", {}).get("name") == "shopping_cart_agent":
                return "Shopping cart management..."
            if chunk[1].get("payload", {}).get("name") == "warehouse_manager_agent":
                return "Warehouse management..."
            if chunk[1].get("payload", {}).get("name") == "tool_node":
                message ="".join([_tool_to_text(tool_call) for tool_call in chunk[1].get('payload',{}).get('input', {}).tool_calls])
                return message
        elif _is_interrupt(chunk):
            value = chunk[1].get('payload', {}).get('interrupts', [])[0].get('value')
            payload = {
                "type": "hitl_interrupt",
                "data": {
                    "data": value
                }
            }
            return json.dumps(payload)
        else:
            return "Unknown operation..."
    
    # 图状态初始化
    if mode == "initialize":
        initial_state = {
            "messages": [{"role": "user", "content": question}],
            "user_id": thread_id,
            "cart_id": thread_id,
            "product_qa_agent": {
                "iteration": 0,
                "final_answer": False,
                "available_tools": product_qa_agent_tool_descriptions,
                "tool_calls": []
            },
            "shopping_cart_agent": {
                "iteration": 0,
                "final_answer": False,
                "available_tools": shopping_cart_agent_tool_descriptions,
                "tool_calls": []
            },
            "warehouse_manager_agent": {
                "iteration": 0,
                "final_answer": False,
                "available_tools": warehouse_manager_agent_tool_descriptions,
                "tool_calls": []
            },
            "coordinator_agent": {
                "iteration": 0,
                "final_answer": False,
                "plan": [],
                "next_agent": ""
            },
        }
    elif mode == "hitl":
        initial_state = Command(
            resume={
                "confirmed": question
            }
        )
    
    # 多轮对话设置 & 多轮对话
    config = {"configurable": {"thread_id": thread_id}}
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
    
    shopping_cart = get_shopping_cart(thread_id, thread_id)
    shopping_cart_items = [
        {
            "price": float(item.get("price")) if item.get("price") else None,
            "quantity": item.get("quantity"),
            "currency": item.get("currency"),
            "product_image_url": item.get("product_image_url"),
            "total_price": float(item.get("total_price")) if item.get("total_price") else None
        }
        for item in shopping_cart
    ]
    
    yield _string_for_sse(json.dumps(
        {
            "type": "final_result",
            "data": {
                "answer": result.get("answer", ""),
                "used_context": used_context,
                "trace_id": result.get("trace_id", ""),
                "shopping_cart": shopping_cart_items
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


