from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.api.middleware import RequestIDMiddleware
from api.api.endpoints import api_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - &(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 初始化 FastAPI 服务器
app = FastAPI()

# 注册中间件
# 所有请求，先经过中间件，再进入接口
app.add_middleware(RequestIDMiddleware)
app.add_middleware(         
    # 允许 Streamlit 前端访问
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
# 接口去 api_router 里面找
app.include_router(api_router)


