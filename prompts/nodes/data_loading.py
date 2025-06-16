from prompts.state.data_load_state import StateDict
from prompts.tools.product_info import get_products_info
from prompts.tools.review_loader import search_reviews_vector

# =============================================
# 노드 함수
# =============================================
def load_reviews_node(state: StateDict) -> StateDict:
    """리뷰 데이터 로드 노드"""
    if state.error:
        return state
    
    user_prompt = state.user_prompt
    product1 = state.product1
    product2 = state.product2
    
    # search_reviews_vector Tool 사용해서 리뷰 검색
    result1 = search_reviews_vector.invoke({"product_id": product1, "user_prompt": user_prompt})
    result2 = search_reviews_vector.invoke({"product_id": product2, "user_prompt": user_prompt})
    
    if not result1["success"] or not result2["success"]:
        return {
            **state,
            "error": f"Failed to load reviews: {result1.get('error', '')} {result2.get('error', '')}"
        }
    
    return {
        "reviews_data1": result1["data"],
        "reviews_data2": result2["data"]
    }


def load_products_node(state: StateDict) -> StateDict:
    """제품 정보 로드 노드"""
    if state.error:
        return state
    
    product1 = state.product1
    product2 = state.product2
    
    # Tool 사용해서 제품 정보 조회
    result = get_products_info.invoke({"product1": product1, "product2": product2})
    
    if not result["success"]:
        return {
            "error": f"Failed to load product info: {result.get('error', '')}"
        }
    
    return {
        "products_data": result["data"]
    }


# =============================================
# 조건부 엣지 함수
# =============================================
def check_error(state: StateDict) -> str:
    """에러 상태 확인"""
    if state.error:
        return "error"
    return "continue"