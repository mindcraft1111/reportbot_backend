from langchain_chroma import Chroma
from prompts.llm.embedding import embeddings


# ==========================================================================================
# 벡터DB 로딩 함수
# ==========================================================================================
def vectordb(id):
    print("제품 id 확인 :", id)
    product = f"./vectordb/reviews/product_{id}"
    vectorstore = Chroma(persist_directory=product, embedding_function=embeddings, collection_name=f"reviews_product_{id}")
    retriever = vectorstore.as_retriever()
    return retriever


def get_context(state: dict) -> str:
    cls = state["classification"]
    question = state["question"]
    product_1 = state["product1"]
    product_2 = state["product2"]

    if cls == "report":
        return get_report_context(question)
    elif cls == "own":
        return get_review_context(question, product_id=product_1, cls="own")
    elif cls == "competitor":
        return get_review_context(question, product_id=product_2, cls="competitor")
    elif cls == "both_products":
        return (
            get_review_context(question, product_id=product_1, cls="own") + "\n\n" +
            get_review_context(question, product_id=product_2, cls="competitor")
        )
    else: # unknown
        return (
            get_review_context(question, product_id=product_1, cls="own") + "\n\n" +
            get_review_context(question, product_id=product_2, cls="competitor") + "\n\n" +
            get_report_context(question)
        )


def get_review_context(question: str, product_id: str, cls: str) -> str:
    retriever = vectordb(product_id)
    docs = retriever.invoke(question)

    # 태그 붙여서 통합
    tag = "[자사]" if cls == "own" else "[타사]"
    review_text = "\n".join([f"{tag} {doc.page_content}" for doc in docs])
    return review_text

def get_report_context(question: str) -> str:
    return "리포트 텍스트"

def get_both_context(question: str) -> str:
    return get_review_context(question) + "\n\n" + get_report_context(question)
