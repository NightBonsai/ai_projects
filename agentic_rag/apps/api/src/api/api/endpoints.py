from starlette.responses import StreamingResponse
from fastapi import Request, APIRouter
import logging

from api.api.models import RAGRequest, RAGResponse, RAGUsedContext, FeedbackRequest, FeedbackResponse
from api.api.processors.submit_feedback import submit_feedback
from api.agents.graph import rag_agent_stream_wrapper
# from api.agents.retrieval_generation import rag_pipeline_wrapper    # 固定写死的 RAG 流程 (已弃用)
# from api.agents.graph import rag_agent_wrapper                      # 非流式输出 (已弃用)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - &(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 提供给前端 Streamlit 调用后端服务的接口
### Agentic RAG 服务接口 ###
# 旧端口: 非流式输出 (已弃用)
# rag_router = APIRouter()        # 初始化接口
# @rag_router.post("/")           # 注册接口
# def rag(                        # 接口处理函数
#     request: Request,
#     payload: RAGRequest
# ) -> RAGResponse:

#     answer = rag_agent_wrapper(payload.query, payload.thread_id)
    
#     return RAGResponse(
#         request_id=request.state.request_id,
#         answer=answer["answer"],
#         used_context=[RAGUsedContext(**used_context) for used_context in answer["used_context"]],
#         trace_id=answer["trace_id"]
#     )

# 新端口: 流式输出
rag_router = APIRouter()        # 初始化接口
@rag_router.post("/")           # 注册接口
def rag(                        # 接口处理函数
    request: Request,
    payload: RAGRequest
) -> StreamingResponse:         # 流式输出

    return StreamingResponse(
        rag_agent_stream_wrapper(payload.query, payload.thread_id),
        media_type="text/event-stream"
    )


### 用户反馈服务接口 ###
feedback_router = APIRouter() 
@feedback_router.post("/")
def send_feedback(
    request: Request,
    payload: FeedbackRequest
) -> FeedbackResponse:

    submit_feedback(payload.trace_id, payload.feedback_score, payload.feedback_text, payload.feedback_source_type)

    return FeedbackResponse(
        request_id=request.state.request_id,
        status="success"
    )


### 总服务接口: 包含多个子接口 ###
# 注册 API 路由，使 FastAPI 知道有哪些后端接口可以向前端提供服务
# 总接口常规结构
# api_router
# ├── rag_router
# ├── feedback_router
# └── ...
api_router = APIRouter()        
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])                          # http://localhost:8000/rag/ 
api_router.include_router(feedback_router, prefix="/submit_feedback", tags=["feedback"])    # http://localhost:8000/submit_feedback/


