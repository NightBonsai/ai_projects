import streamlit as st
import requests
import uuid

from chatbot_ui.core.config import config


# Streamlit 每次用户交互都会重新执行整个 Python 文件
# 初始化 Streamlit 前端布局
st.set_page_config(
    page_title="Ecommerce Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 多轮对话设置: 随机设置当前会话 thread_id
def get_session_id():
    if 'session_id' not in st.session_state:
        st.session_state.session_id=str(uuid.uuid4())
    return st.session_state.session_id

session_id = get_session_id()


# 前后端 Streamlit & FastAPI 通信统一接口
def api_call(method, url, **kwargs):

    def _show_error_popup(message):
        """Show error message as a popup in the top-right corner."""
        st.session_state["error_popup"] = {
            "visible": True,
            "message": message,
        }

    try:
        response = getattr(requests, method)(url, **kwargs)

        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = {"message": "Invalid response format from server"}

        if response.ok:
            return True, response_data

        return False, response_data

    except requests.exceptions.ConnectionError:
        _show_error_popup("Connection error. Please check your network connection.")
        return False, {"message": "Connection error"}
    except requests.exceptions.Timeout:
        _show_error_popup("The request timed out. Please try again later.")
        return False, {"message": "Request timeout"}
    except Exception as e:
        _show_error_popup(f"An unexpected error occurred: {str(e)}")
        return False, {"message": str(e)}


# Session State 初始化： 保存聊天记录
# 第一次进入网页时初始化
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can i assist you today?"}
    ]

# 根据历史聊天记录重新渲染聊天窗口
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sidebar 初始化
if "used_context" not in st.session_state:
    st.session_state.used_context = []

# Sidebar 显示回答引用的商品推荐信息
with st.sidebar:
    # Create tabs in the sidebar
    suggestions_tab, = st.tabs(["Suggestions"])
    
    # Suggestions Tab
    with suggestions_tab:
        if st.session_state.used_context:
            for idx, item in enumerate(st.session_state.used_context):  # 遍历每一个商品
                st.caption(item.get('description', 'No description'))        # 商品描述
                if 'image_url' in item:                                      # 商品图片
                    st.image(item["image_url"], width=250)
                st.caption(f"Price: {item['price']} USD")                    # 商品价格
                st.divider()
        else:
            st.info("No suggestions yet")

# Chat Input
if prompt := st.chat_input("Hello! How can I assist you today?"):

    # 保存用户消息到聊天历史
    st.session_state.messages.append({"role":"user", "content": prompt})

    # 聊天窗口立即显示用户输入
    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant 回答
    with st.chat_message("assistant"):
        status, output = api_call(
            "post", 
            f"{config.API_URL}/rag", 
            json={"query": prompt, "thread_id": session_id} # 调用 FastAPI 后端接口
        )  
        
        answer = output["answer"]                       # 提取 llm 最终回答
        used_context = output["used_context"]           # 提取 llm 从知识库真正引用的商品信息

        st.session_state.used_context = used_context    # 引用知识库信息保存到 Session State，Sidebar 会读取这里的数据

        st.write(answer)                                # 主聊天窗口显示 llm 回答

    st.session_state.messages.append({"role":"assistant", "content":answer})    # 保存 Assistant 回复
    st.rerun()                                                                  # 重新运行整个 Streamlit 页面