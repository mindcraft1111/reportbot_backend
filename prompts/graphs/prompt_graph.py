from langgraph.graph import StateGraph, END
from prompts.state.prompt_state import PromptState
from prompts.nodes.response_generation import generate_prompt_node
from prompts.nodes.response_validation import validate_prompt_node


# =============================================
# 그래프 구성
# =============================================
def create_ai_response_graph():
    """AI 응답 생성 및 검증 그래프 생성"""
    workflow = StateGraph(PromptState)

    # 노드 추가
    workflow.add_node("GENERATE", generate_prompt_node)
    workflow.add_node("VALIDATE", validate_prompt_node)

    # 엣지 설정
    workflow.set_entry_point("GENERATE")
    workflow.add_edge("GENERATE", "VALIDATE")

    # 조건부 엣지
    workflow.add_conditional_edges(
        "VALIDATE",
        lambda state: "RETRY" if getattr(state, "validation_error", None) else "DONE", # 분기 함수
        {
            "RETRY": "GENERATE",
            "DONE": END
        }
    )

    return workflow.compile()
