from pydantic import BaseModel, Field
from typing import List

from langsmith import traceable, get_current_run_tree

from langchain_core.messages import convert_to_openai_messages

from openai import OpenAI
from dotenv import load_dotenv
import instructor

from api.agents.utils.utils import format_ai_message
from api.agents.utils.prompt_management import prompt_template_config


load_dotenv()


# 数据模型 (数据结构) → 结构化输出 (LLM 必须按照指定数据结构输出 JSON)
### QnA Agent Response Model ###
class ToolCall(BaseModel):
    name: str
    arguments: dict

class RAGUsedContext(BaseModel):
    id: str = Field(description="The ID of the item used to answer the question")
    description: str = Field(description="Short description of the item used to answer the question")

class AgentResponse(BaseModel):
    answer: str = Field(description="Answer to the question.")
    references: List[RAGUsedContext] = Field(description="List of items used to answer the question.")
    final_answer: bool = False
    tool_calls: List[ToolCall] = []


### Intent Router Response Model ###
class IntentRouterResponse(BaseModel):
    question_relevant: bool
    answer: str


# LangGraph Workflow Node
### Intent Router Agent Node ###
@traceable(
    name="intent_router_node",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-4.1-mini"}
)
def intent_router_node(state):

    # 获取 Prompt
    template = prompt_template_config("api/agents/prompts/intent_router_agent.yaml", "intent_router_agent")
    prompt = template.render()
    
    # 获取当前 Conversation 
    conversation = []
    messages = state.messages
    for message in messages:
        conversation.append(convert_to_openai_messages(message))

    # LLM 根据 Prompt 思考
    # 用户问题是否属于库存商品 ( 属于 返回 True / 不属于 返回 False )
    client = instructor.from_openai(OpenAI())
    response, raw_response = client.chat.completions.create_with_completion(
        model="gpt-4.1-mini",
        response_model=IntentRouterResponse,
        messages=[{"role": "system", "content": prompt}, *conversation],
        temperature=0.5,
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

    return {
        "question_relevant": response.question_relevant,
        "answer": response.answer,
        "trace_id": trace_id
    }


### QnA Agent Node ###
@traceable(
    name="agent_node",
    run_type="llm",
    metadata={"ls_provider": "openai", "ls_model_name": "gpt-4.1-mini"}
)
def agent_node(state) -> dict:

    # 获取 Prompt
    template = prompt_template_config("api/agents/prompts/qa_agent.yaml", "qa_agent")
    prompt = template.render(
        available_tools=state.available_tools
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
        model="gpt-4.1-mini",
        response_model=AgentResponse,
        messages=[{"role": "system", "content": prompt}, *conversation],
        temperature=0.5
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
        "tool_calls": response.tool_calls,
        "iteration": state.iteration + 1,
        "answer": response.answer,
        "final_answer": response.final_answer,
        "references": response.references
    }


