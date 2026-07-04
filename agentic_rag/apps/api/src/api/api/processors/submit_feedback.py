from langsmith import Client


ls_client = Client()


def submit_feedback(trace_id: str, feedback_score: int = None, feedback_text: str = "", feedback_source_type: str ="api") -> None:
    
    # 记录用户反馈
    # 满意
    if feedback_score:
        ls_client.create_feedback(
            run_id=trace_id,
            key="thumbs",
            score=feedback_score,
            feedback_source_type=feedback_source_type
        )

    # 不满意
    if len(feedback_text) > 0:
        ls_client.create_feedback(
            run_id=trace_id,
            key="comment",
            value=feedback_text,
            score=feedback_score,   # 新增
            feedback_source_type=feedback_source_type
        )
        