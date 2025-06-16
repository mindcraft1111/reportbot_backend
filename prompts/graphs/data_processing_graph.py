from langgraph.graph import StateGraph, END
from prompts.state.data_load_state import StateDict
from prompts.nodes.context_merge import combine_data_node
from prompts.nodes.data_loading import load_reviews_node, load_products_node, check_error


# =============================================
# 그래프 구성
# =============================================
def create_data_processing_graph():
    """데이터 처리 그래프 생성"""
    workflow = StateGraph(StateDict)
    
    # 노드 추가
    workflow.add_node("load_reviews", load_reviews_node)
    workflow.add_node("load_products", load_products_node)
    workflow.add_node("combine_data", combine_data_node)
    
    # 엣지 설정
    workflow.set_entry_point("load_reviews")
    
    # 조건부 엣지    
    workflow.add_conditional_edges(
        "load_reviews",
        check_error,
        {
            "error": END,
            "continue": "load_products"
        }
    )
    
    workflow.add_conditional_edges(
        "load_products",
        check_error,
        {
            "error": END,
            "continue": "combine_data"
        }
    )
    
    workflow.add_edge("combine_data", END)
    
    return workflow.compile()
