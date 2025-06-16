import logging
from langchain_core.tools import tool
from prompts.llm.vector_db import VectorDBWrapper


# 리뷰 문서 포맷팅
def format_docs(docs: list, tag: str) -> str:
    return "\n".join([
        f"[{tag} 리뷰]: {doc.page_content}\n[메타데이터]: {doc.metadata}"
        for doc in docs
    ])


@tool(description="벡터 데이터베이스에서 제품 리뷰를 검색합니다.")
def search_reviews_vector(product_id: str, user_prompt:str)-> dict:
     
    if not user_prompt:
        raise ValueError("Prompt is required")  # Django response 말고 예외로 처리
    try:
        # ChromaDB 연결
        vectordb = VectorDBWrapper(product_id)

        # 검색 실행
        docs = vectordb.search(user_prompt)

        # 결과 포맷팅
        reviews_data = format_docs(docs, f"제품{product_id}")

        return {
            "success": True,
            "data": reviews_data,
            "count": len(docs)
        }

    except Exception as e:
        logging.error(f"Error searching reviews for product {product_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": ""
        }

    except Exception as e:
        logging.error(f"Error searching reviews for product {product_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": ""
        }
