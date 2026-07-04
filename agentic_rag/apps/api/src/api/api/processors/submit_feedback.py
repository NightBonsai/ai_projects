from langsmith import Client


ls_client = Client()


def submit_feedback(trace_id: str, feedback_score: int = None, feedback_text: str = "", feedback_source_type: str ="api") -> None:
    
    if feedback_score:
        ls_client.create_feedback(
            run_id=trace_id,
            key="thumbs",
            score=feedback_score,
            feedback_source_type=feedback_source_type
        )

    if len(feedback_text) > 0:
        ls_client.create_feedback(
            run_id=trace_id,
            key="comment",
            value=feedback_text,
            feedback_source_type=feedback_source_type
        )
        