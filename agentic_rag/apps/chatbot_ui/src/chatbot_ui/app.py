import streamlit as st
import requests
import uuid
import logging
import json

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
# 非流式输出接口
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

# 流式输出接口
def api_call_stream(method, url, **kwargs):

    def _show_error_popup(message):
        """Show error message as a popup in the top-right corner."""
        st.session_state["error_popup"] = {
            "visible": True,
            "message": message,
        }
    
    try:
        response = getattr(requests, method)(url, **kwargs)
    
        return response.iter_lines()
    
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


### 提交用户 Human in the loop 接口 ###
# def send_hitl_response(thread_id: str, approved: bool, feedback: str = None):
#     """Send HITL response to the API endpoint"""
#     hitl_data = {
#         "thread_id": thread_id,
#         "approved": approved,
#         "feedback": feedback
#     }
#     status, response = api_call("post", f"{config.API_URL}/send_hitl_response", json=hitl_data)
#     return status, response

### Human in the loop 弹出窗口 ###
@st.dialog("Human Review Required")
def hitl_popup(task_data: dict):
    """Modal popup that blocks the graph until human responds."""
    st.markdown(f"**Agent wants to proceed with:**")
    st.json(task_data)

    feedback = st.text_area("Your feedback (optional):", key="hitl_feedback")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve", type="primary", use_container_width=True):
            # send_hitl_response(session_id, approved=True, feedback=feedback)
            st.session_state.pending_hitl = None
            st.session_state.hitl_decision = {"approved": True, "feedback": feedback}
            st.rerun()
    with col2:
        if st.button("Reject", use_container_width=True):
            # send_hitl_response(session_id,approved=False, feedback=feedback)
            st.session_state.pending_hitl = None
            st.session_state.hitl_decision = {"approved": False, "feedback": feedback}
            st.rerun()


# Session State 初始化： 保存聊天记录
# 第一次进入网页时初始化
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can i assist you today?"}]

# 根据历史聊天记录重新渲染聊天窗口 (已弃用，User Feedback 中重新实现)
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# Sidebar 初始化
if "used_context" not in st.session_state:
    st.session_state.used_context = []

if "shopping_cart" not in st.session_state:                 # Initialize feedback states (simplified)
    st.session_state.shopping_cart = []

if "pending_hitl" not in st.session_state:
    st.session_state.pending_hitl = None

if "latest_feedback" not in st.session_state:               # Initialize feedback states (simplified)
    st.session_state.latest_feedback = None

if "show_feedback_box" not in st.session_state:             # Initialize feedback states (simplified)
    st.session_state.show_feedback_box = False

if "feedback_submission_status" not in st.session_state:    # Initialize feedback states (simplified)
    st.session_state.feedback_submission_status = None

if "trace_id" not in st.session_state:                      # Initialize feedback states (simplified)
    st.session_state.trace_id = None

if st.session_state.pending_hitl:
    hitl_popup(st.session_state.pending_hitl)

if "hitl_decision" not in st.session_state:
    st.session_state.hitl_decision = None


# Process HITL decision - stream the resumed graph response
if st.session_state.hitl_decision is not None:
    decision = st.session_state.hitl_decision
    st.session_state.hitl_decision = None

    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        message_placeholder = st.empty()

        for line in api_call_stream(
            "post",
            f"{config.API_URL}/send_hitl_response",
            json={
                "thread_id": session_id,
                "approved": decision["approved"],
                "feedback": decision.get("feedback"),
            },
            stream=True,
            headers={"Accept": "text/event-stream"},
        ):
            line_text = line.decode("utf-8")
            if line_text.startswith("data: "):
                data = line_text[6:]
                try:
                    output = json.loads(data)
                    if output["type"] == "final_result":
                        answer = output["data"]["answer"]
                        used_context = output["data"]["used_context"]
                        trace_id = output["data"]["trace_id"]
                        shopping_cart = output["data"]["shopping_cart"]
            
                        st.session_state.used_context =used_context
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.session_state.trace_id = trace_id
                        st.session_state.shopping_cart = shopping_cart
                        st.session_state.latest_feedback = None
                        st.session_state.show_feedback_box = False
                        st.session_state.feedback_submission_status = None

                        status_placeholder.empty()
                        message_placeholder.markdown(answer)
                        break
                except json.JSONDecodeError:
                    status_placeholder.markdown(f"*{data}*")
    st.rerun()


# Sidebar 显示商品推荐信息 & 购物车
with st.sidebar:
    # Create tabs in the sidebar
    suggestions_tab, shopping_cart_tab = st.tabs(["Suggestions", "Shopping Cart"])
    
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
    
    # Shopping Cart Tab
    with shopping_cart_tab:
        if st.session_state.shopping_cart:
            for idx, item in enumerate(st.session_state.shopping_cart): # 遍历每一个商品
                st.caption(item.get('description', 'No description'))        # 商品描述
                if 'product_image_url' in item:
                    st.image(item["product_image_url"], width=250)
                st.caption(f"Price: {item['price']} {item['currency']}")
                st.caption(f"Quantity: {item['quantity']}")
                st.caption(f"Total price: {item['total_price']} {item['currency']}")
                st.divider()
        else:
            st.info("Your cart is empty")


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

        # 流式输出
        status_placeholder = st.empty()
        message_placeholder = st.empty()
        for line in api_call_stream(                    # 调用 FastAPI 后端接口: 流式输出形式
            "post",
            f"{config.API_URL}/agent",
            json={"query": prompt, "thread_id": session_id},    
            stream=True,
            headers={"Accept": "text/event-stream"}
        ):
            line_text = line.decode("utf-8")
            if line_text.startswith("data: "):
                data = line_text[6:]
            
                try:
                    output = json.loads(data)

                    if output["type"] == "final_result":
                        answer = output["data"]["answer"]               # 提取 llm 最终回答
                        used_context = output["data"]["used_context"]   # 提取 llm 从知识库真正引用的商品信息
                        trace_id = output["data"]["trace_id"]
                        shopping_cart = output["data"]["shopping_cart"]

                        st.session_state.used_context = used_context    # 引用知识库信息保存到 Session State，Sidebar 会读取这里的数据
                        st.session_state.messages.append({"role": "assistant", "content": answer})  # 保存 Assistant 回复
                        st.session_state.trace_id = trace_id
                        st.session_state.shopping_cart = shopping_cart

                        st.session_state.latest_feedback = None
                        st.session_state.show_feedback_box = False
                        st.session_state.feedback_submission_status = None

                        status_placeholder.empty()
                        message_placeholder.markdown(answer)    # 主聊天窗口显示 llm 回答
                        break

                    elif output["type"] == "hitl_interrupt":
                        st.session_state.pending_hitl = output["data"]
                        break
                
                except json.JSONDecodeError:
                    status_placeholder.markdown(f"*{data}*")

        # 非流式输出 (已弃用)
        # status, output = api_call(
        #     "post", 
        #     f"{config.API_URL}/rag", 
        #     json={"query": prompt, "thread_id": session_id} # 调用 FastAPI 后端接口
        # )  
        
        # answer = output["answer"]                       # 提取 llm 最终回答
        # used_context = output["used_context"]           # 提取 llm 从知识库真正引用的商品信息
        # trace_id = output["trace_id"]

        # st.session_state.used_context = used_context    # 引用知识库信息保存到 Session State，Sidebar 会读取这里的数据
        # st.session_state.trace_id = trace_id            

        # st.write(answer)                                # 主聊天窗口显示 llm 回答

    # st.session_state.messages.append({"role":"assistant", "content": answer})    # 保存 Assistant 回复
    st.rerun()                                                                   # 重新运行整个 Streamlit 页面