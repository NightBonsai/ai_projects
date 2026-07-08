from pydantic import BaseModel, Field
from typing import List

from langsmith import traceable, get_current_run_tree

from langchain_core.messages import convert_to_openai_messages
from langchain_core.messages import AIMessage

from openai import OpenAI
from dotenv import load_dotenv
import instructor

from api.agents.utils.utils import format_ai_message
from api.agents.utils.prompt_management import prompt_template_config


load_dotenv()


#### Coordinator Agent ####
### Coordinator Agent Response Model ###
# 数据模型 (数据结构) → 结构化输出 (LLM 必须按照指定数据结构输出 JSON)
class Delegation(BaseModel):
    agent: str
    task: str

class CoordinatorAgentResponse(BaseModel):
    next_agent: str
    plan: List[Delegation]
    final_answer: bool = False
    answer: str = ""


### Coordinator Agent Node ###
# LangGraph Workflow Node
@traceable(
    name="coordinator_agent",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-4.1"}
)
def coordinator_agent(state) -> dict:

    # 获取 Prompt
    template = prompt_template_config("api/agents/prompts/coordinator_agent.yaml", "coordinator_agent")  
    prompt = template.render()
    
    # 获取当前 Conversation 
    conversation = []
    messages = state.messages
    for message in messages:
        conversation.append(convert_to_openai_messages(message))

    # LLM 根据 Prompt 思考
    # 是否调用 Tool or 是否已经得到最终答案
    client = instructor.from_openai(OpenAI())
    response, raw_response = client.chat.completions.create_with_completion(
        model="gpt-4.1",
        response_model=CoordinatorAgentResponse,
        messages=[{"role": "system", "content": prompt}, *conversation],
        temperature=0,
    )
    
    # LangSmith 记录 Token 使用情况 & 当前对话 Trace ID
    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens
        }
        trace_id = str(getattr(current_run, "trace_id", current_run.id))
    else:
        trace_id = None

    if response.final_answer:
        ai_message = [AIMessage(content=response.answer,)]
    else:
        ai_message = []

    return {
        "messages": ai_message,
        "answer": response.answer,
        "coordinator_agent": {
            "iteration": state.coordinator_agent.iteration + 1,
            "final_answer": response.final_answer,
            "next_agent": response.next_agent,
            "plan": [data.model_dump() for data in response.plan]
        },
        # "trace_id": trace_id
    }


#### Product QnA Agent ####
### Product QnA Agent Response Model ###
# 数据模型 (数据结构) → 结构化输出 (LLM 必须按照指定数据结构输出 JSON)
class ToolCall(BaseModel):
    name: str
    arguments: dict

class RAGUsedContext(BaseModel):
    id: str = Field(description="The ID of the item used to answer the question")
    description: str = Field(description="Short description of the item used to answer the question")

class ProductQAAgentResponse(BaseModel):
    answer: str = Field(description="Answer to the question.")
    references: List[RAGUsedContext] = Field(description="List of items used to answer the question.")
    final_answer: bool = False
    tool_calls: List[ToolCall] = []


### Product QnA Agent Node ###
# LangGraph Workflow Node
@traceable(
    name="product_qa_agent",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-4.1"}
)
def product_qa_agent(state) -> dict:

    # 获取 Prompt
    template = prompt_template_config("api/agents/prompts/product_qa_agent.yaml", "product_qa_agent")
    prompt = template.render(
        available_tools=state.product_qa_agent.available_tools
    )

    # 获取当前 Conversation 
    conversation = []
    messages = state.messages
    for message in messages:
        conversation.append(convert_to_openai_messages(message))
    
    # LLM 根据 Prompt 思考
    # 是否调用 Tool or 是否已经得到最终答案
    client = instructor.from_openai(OpenAI())
    response, raw_response = client.chat.completions.create_with_completion(
        model="gpt-4.1",
        response_model=ProductQAAgentResponse,
        messages=[{"role": "system", "content": prompt}, *conversation],
        temperature=0
    )
    ai_message = format_ai_message(response)        # 将 Instructor 输出转换为 LangChain AIMessage

    # LangSmith 记录 Token 使用情况
    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens
        }

    return {
        "messages": [ai_message],
        "product_qa_agent":{
            "tool_calls": [tool_call.model_dump() for tool_call in response.tool_calls],
            "iteration": state.product_qa_agent.iteration + 1,
            "final_answer": response.final_answer,
            "available_tools": state.product_qa_agent.available_tools
        },
        "answer": response.answer,
        "references": response.references
    }


#### Shopping Cart Agent ####
### Shopping Cart Agent Response Model ###
# 数据模型 (数据结构) → 结构化输出 (LLM 必须按照指定数据结构输出 JSON)
class ShoppingCartAgentResponse(BaseModel):
    answer: str= Field(description="Answer to the question.")
    final_answer: bool = False
    tool_calls: List[ToolCall] = []


### Shopping Cart Agent Node ###
# LangGraph Workflow Node
@traceable(
    name="shopping_cart_agent",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-4.1"}
)
def shopping_cart_agent(state) -> dict:
    
    # 获取 Prompt
    template = prompt_template_config("api/agents/prompts/shopping_cart_agent.yaml", "shopping_cart_agent")    
    prompt = template.render(
        available_tools=state.shopping_cart_agent.available_tools,
        user_id=state.user_id,
        cart_id=state.cart_id
    )

    # 获取当前 Conversation 
    conversation = []
    messages = state.messages
    for message in messages:
        conversation.append(convert_to_openai_messages(message))
    
    # LLM 根据 Prompt 思考
    # 是否调用 Tool or 是否已经得到最终答案
    client = instructor.from_openai(OpenAI())
    response, raw_response = client.chat.completions.create_with_completion(
        model="gpt-4.1",
        response_model=ShoppingCartAgentResponse,
        messages=[{"role": "system", "content": prompt}, *conversation],
        temperature=0
    )
    ai_message = format_ai_message(response)        # 将 Instructor 输出转换为 LangChain AIMessage

    # LangSmith 记录 Token 使用情况
    current_run = get_current_run_tree()
    if current_run:
        current_run.metadata["usage_metadata"] = {
            "input_tokens": raw_response.usage.prompt_tokens,
            "output_tokens": raw_response.usage.completion_tokens,
            "total_tokens": raw_response.usage.total_tokens
        }

    return {
        "messages": [ai_message],
        "shopping_cart_agent":{
            "tool_calls": [tool_call.model_dump() for tool_call in response.tool_calls],
            "iteration": state.shopping_cart_agent.iteration + 1,
            "final_answer": response.final_answer,
            "available_tools": state.shopping_cart_agent.available_tools
        },
        "answer": response.answer,
    }

