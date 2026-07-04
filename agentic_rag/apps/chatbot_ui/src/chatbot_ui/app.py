import streamlit as st
import requests
import uuid
import logging

from chatbot_ui.core.config import config


# 初始化日志设置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
### Agentic RAG 接口 ###
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


### 提交用户反馈接口 ###
def submit_feedback(feedback_type=None, feedback_text=""):
    """Submit feedback to the API endpoint"""

    def _feedback_score(feedback_type):
        if feedback_type == "positive":
            return 1
        elif feedback_type == "negative":
            return 0
        else:
            return None

    feedback_data = {
        "feedback_score": _feedback_score(feedback_type),
        "feedback_text": feedback_text,
        "trace_id": st.session_state.trace_id,
        "thread_id": session_id,
        "feedback_source_type": "api"
    }

    logger.info(f"Feedback data: {feedback_data}")

    status, response = api_call("post", f"{config.API_URL}/submit_feedback", json=feedback_data)
    return status, response


# Session State 初始化： 保存聊天记录
# 第一次进入网页时初始化
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can i assist you today?"}
    ]

# 根据历史聊天记录重新渲染聊天窗口 (已弃用，User Feedback 中重新实现)
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# Sidebar 初始化
if "used_context" not in st.session_state:
    st.session_state.used_context = []

if "latest_feedback" not in st.session_state:               # Initialize feedback states (simplified)
    st.session_state.latest_feedback = None

if "show_feedback_box" not in st.session_state:             # Initialize feedback states (simplified)
    st.session_state.show_feedback_box = False

if "feedback_submission_status" not in st.session_state:    # Initialize feedback states (simplified)
    st.session_state.feedback_submission_status = None

if "trace_id" not in st.session_state:                      # Initialize feedback states (simplified)
    st.session_state.trace_id = None

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


# User Feedback
# 根据历史聊天记录重新渲染聊天窗口
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Add feedback buttons only for the latest assistant message (excluding the initial greeting)
        is_latest_assistant = (
            message["role"] == "assistant" and
            idx == len(st.session_state.messages) - 1 and
            idx > 0
        )

        if is_latest_assistant:
            # Use Streamlit's built-in feedback component
            feedback_key = f"feedback_{len(st.session_state.messages)}"
            feedback_result = st.feedback("thumbs", key=feedback_key)

            # Handle feedback selection
            if feedback_result is not None:
                feedback_type = "positive" if feedback_result == 1 else "negative"

                # Only submit if this is a new/different feedback
                if st.session_state.latest_feedback != feedback_type:
                    with st.spinner("Submitting feedback..."):
                        status, response = submit_feedback(feedback_type=feedback_type)
                        if status:
                            st.session_state.latest_feedback = feedback_type
                            st.session_state.feedback_submission_status = "success"
                            st.session_state.show_feedback_box = (feedback_type == "negative")
                        else:
                            st.session_state.feedback_submission_status = "error"
                            st.error("Failed to submit feedback.Please try again.")
                    st.rerun()

            # Show feedback status message
            if st.session_state.latest_feedback and st.session_state.feedback_submission_status == "success":
                if st.session_state.latest_feedback == "positive":
                    st.success("Thank you for your positive feedback!")
                elif st.session_state.latest_feedback == "negative" and not st.session_state.show_feedback_box:
                    st.success("Thank you for your feedback!")
            elif st.session_state.feedback_submission_status == "error":
                st.error("Failed to submit feedback. Please try again.")
            
            # Show feedback text box if thumbs down was pressed
            if st.session_state.show_feedback_box:
                st.markdown("**want to tell us more? (Optional)**")
                st.caption("Your negative feedback has already been recorded. You can optionally provide additional details below.")
            
                # Text area for detailed feedback
                feedback_text = st.text_area(
                    "Additional feedback (optional)",
                    key=f"feedback_text_{len(st.session_state.messages)}",
                    placeholder="Please describe what was wrong with this response...",
                    height=108
                )
                
                # Send additional feedback button
                col_send, col_spacer, col_close = st.columns([3, 5, 2])
                with col_send:
                    if st.button("Send Additional Details", key=f"send_additional_{len(st.session_state.messages)}"):
                        if feedback_text.strip():   # Only send if there's actual text
                            with st.spinner("Submitting additional feedback..."):
                                status, response = submit_feedback(feedback_text=feedback_text)
                                if status:
                                    st.success("Thank you! Your additional feedback has been recorded.")
                                    st.session_state.show_feedback_box=False
                                else:
                                    st.error("Failed to submit additional feedback. Please try again.")
                        else:
                            st.warning("Please enter some feedback text before submitting.")
                        st.rerun()

                with col_close:
                    if st.button("Close", key=f"close_feedback_{len(st.session_state.messages)}"):
                        st.session_state.show_feedback_box = False
                        st.rerun()


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
        trace_id = output["trace_id"]

        st.session_state.used_context = used_context    # 引用知识库信息保存到 Session State，Sidebar 会读取这里的数据
        st.session_state.trace_id = trace_id            

        st.write(answer)                                # 主聊天窗口显示 llm 回答

    st.session_state.messages.append({"role":"assistant", "content":answer})    # 保存 Assistant 回复
    st.rerun()                                                                  # 重新运行整个 Streamlit 页面