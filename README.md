# ai_projects

### 开发环境

Windows11

Docker

Python 3.12 or 3.14

uv python包管理器

cursor IDE

### 已完成内容

1. 项目原型构建: 
   - Streamlit 前端 
   - FastAPI 后端
2. RAG 系统实现：
   - 数据集获取 & 提取
   - Qdrant 向量数据库部署
   - 数据集 Embedding 处理 & 存入数据库
   - RAG 流程实现
   - LangSmith 可观测 debug 平台部署
   - 测试集生成 & 存入数据库
   - 结构化输出实现
   
     ```
     Pydantic + Instructor
     ```
   - 混合检索实现
   
     ```
     Embedding 相似度 + 关键词检索 
     ```



### 环境搭建

1. 安装 Python 3.12 or 3.14

   [Python ]: https://www.python.org/

2. 安装 uv

   [UV ]: https://docs.astral.sh/uv/getting-started/installation/

3. 安装 cursor IDE

   [Cursor IDE]: https://cursor.com/

4. 安装 Docker Desktop 并运行

   [Docker Desktop]: https://www.docker.com/

5. 安装指定项目虚拟环境 

   - 指定项目 根目录 下执行

     ```
     uv sync
     ```

6. 选择 Python Interpreter

   - Cursor IDE 中选择

     ```
     Ctrl + Shift + P
     ```

7. 按照 env.example 的格式设置 .env

8. 往 Qdrant 向量数据库中录入数据

   - 录入方式详见 notbooks

9. 启动指定项目

   - 指定项目 根目录 下执行

     ```
     uv sync
     docker compose up --build
     ```

   - 通过浏览器访问 FastAPI 后端服务，Streamlit 前端服务和 Qdrant 向量数据库

     ```
     http://localhost:8501
     http://localhost:8000/docs
     http://localhost:6333/dashboard
     ```

     



