from fastapi import Request, APIRouter
import logging

from api.api.models import RAGRequest, RAGResponse
from api.agents.retrieval_generation import rag_pipeline    # RAG


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - &(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 提供给前端 Streamlit 调用后端服务的接口
rag_router = APIRouter()        # 初始化接口
@rag_router.post("/")           # 注册接口
def rag(                        # 接口处理函数
    request: Request,
    payload: RAGRequest
) -> RAGResponse:
    answer = rag_pipeline(payload.query)
    return RAGResponse(
        request_id=request.state.request_id,
        answer=answer
    )

api_router = APIRouter()        # 初始化总接口: 包含多个子接口
api_router.include_router(
    # 注册 API 路由，使 FastAPI 知道有哪些后端接口可以向前端提供服务
    # 总接口常规结构
    # api_router
    # ├── rag_router
    # ├── xxx_router
    # └── ...
    rag_router, 
    prefix="/rag",              # http://localhost:8000/rag/
    tags=["rag"]
)

