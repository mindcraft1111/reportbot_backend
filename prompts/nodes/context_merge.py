from prompts.state.data_load_state import StateDict


def combine_data_node(state: StateDict) -> StateDict:
    """데이터를 결합하는 노드"""
    if state.error:
        return state
    
    reviews_data1 = state.reviews_data1
    reviews_data2 = state.reviews_data2
    products_data = state.products_data
    
    final_docs = f"{reviews_data1}\n\n{reviews_data2}\n\n{products_data}"
    
    return {
        "final_docs": final_docs,
    }