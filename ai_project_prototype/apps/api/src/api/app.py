from fastapi import FastAPI, Request
from pydantic import BaseModel

from openai import OpenAI
from google import genai

from api.core.config import config

import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - &(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_llm(provider, model_name, messages, reasoning_effort="minimal", max_tokens=500):
    if provider == "OpenAI":
        client = OpenAI(api_key=config.OPENAI_API_KEY)
    elif provider == "Google":
        client = genai.Client(api_key=config.GOOGLE_API_KEY)
    elif provider == "DeepSeek":
        client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    elif provider == "Zhipu":
        client = OpenAI(api_key=config.ZHIPU_API_KEY, base_url="https://open.bigmodel.cn/api/paas/v4")
    
    if provider == "Google":
        return client.models.generate_content(
            model=model_name,
            contents=[message["content"] for message in messages],
        ).text
    elif provider in ["DeepSeek", "Zhipu"]:
        return client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_completion_tokens=max_tokens,
        ).choices[0].message.content
    else:
        return client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_completion_tokens=max_tokens,
            reasoning_effort=reasoning_effort
        ).choices[0].message.content


# 数据结构
class ChatRequest(BaseModel):
    provider: str
    models_name: str
    messages: list[dict]

class ChatResponse(BaseModel):
    message: str


# 提供给前端 Streamlit 调用后端服务的接口
app = FastAPI()         # 初始化接口
@app.post("/chat")      # 注册接口
def chat(               # 接口处理函数
    request: Request,
    payload: ChatRequest
) -> ChatResponse:
    result = run_llm(payload.provider, payload.models_name, payload.messages)
    return ChatResponse(message = result)

