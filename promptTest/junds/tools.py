from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool

from .embeddings import SentenceTransformerEmbeddings
from .config import DB_ENGINE

import json
import re
import pandas as pd


# =============================================
# 분석 타입 분류 도구
# =============================================
@tool(
    description="사용자 프롬프트를 분석해서 벡터 검색 또는 메트릭 분석 중 어느 것이 적합한지 판단합니다."
)
def classify_analysis_type(user_prompt: str) -> dict:
    """
    사용자 프롬프트를 분석해서 적절한 분석 방법을 결정합니다.
    - vector: 정성적 분석, 리뷰 내용 분석, 감정 분석 등
    - metrics: 정량적 분석, 통계, 수치 계산 등
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    classification_prompt = PromptTemplate.from_template(
        """
        다음 사용자 요청을 분석해서 어떤 분석 방법이 적합한지 판단해주세요:

        1. **vector**: 정성적 분석이 필요한 경우
           - 리뷰 내용의 감정이나 의견 분석
           - 특정 키워드나 주제에 대한 언급 분석
           - 전반적인 사용자 경험이나 만족도 분석
           - "어떤 느낌인지", "사용자들이 뭐라고 하는지" 등

        2. **metrics**: 정량적 분석이 필요한 경우
           - 평점, 별점 등 수치 데이터 분석
           - 통계적 비교 (평균, 최고, 최저 등)
           - 데이터 집계나 계산
           - "평균 평점은?", "몇 개의 리뷰가?", "비율은?" 등

        다음 형식으로만 JSON 응답해주세요:
        ```json
        {{
        "analysis_type": "vector" | "metrics",
        "reason": "간단한 설명"
        }}
        ```

        사용자 요청: {prompt}
        답:
        """
    )

    result = llm.invoke(classification_prompt.format(prompt=user_prompt))
    content = result.content.strip()

    try:
        json_text = re.sub(r"^```json\s*|```$", "", content).strip()
        parsed = json.loads(json_text)
        return {"analysis_type": parsed["analysis_type"], "reason": parsed["reason"]}
    except Exception as e:
        # 기본값으로 vector 선택
        return {"analysis_type": "vector", "reason": "분류 실패로 기본 벡터 검색 선택"}


# =============================================
# 벡터 검색 기반 분석 도구
# =============================================
@tool(description="ChromaDB를 사용한 벡터 검색으로 리뷰 데이터를 분석합니다.")
def vector_analysis(user_prompt: str, product1: str, product2: str) -> dict:
    if not user_prompt:
        raise ValueError("Prompt is required")

    # 임베딩 모델 로드
    embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")
    embeddings = SentenceTransformerEmbeddings(embedding_model)

    # ChromaDB 불러오기
    vectordb1 = Chroma(
        persist_directory=f"../vectordb/reviews/product_{product1}",
        collection_name=f"reviews_product_{product1}",
        embedding_function=embeddings,
    )
    vectordb2 = Chroma(
        persist_directory=f"../vectordb/reviews/product_{product2}",
        collection_name=f"reviews_product_{product2}",
        embedding_function=embeddings,
    )

    # retriever 설정
    retriever1 = vectordb1.as_retriever(search_kwargs={"k": 30})
    retriever2 = vectordb2.as_retriever(search_kwargs={"k": 30})

    # MySQL에서 product 정보 로드
    query = f"SELECT * FROM products WHERE id IN ({product1}, {product2})"
    products_df = pd.read_sql(query, con=DB_ENGINE)

    # 리뷰 검색
    docs1 = retriever1.invoke(user_prompt)
    docs2 = retriever2.invoke(user_prompt)

    # 컨텍스트 구성
    reviews_data1 = "\n".join(
        [
            f"[제품1 리뷰]: {doc.page_content}\n[메타데이터]: {doc.metadata}"
            for doc in docs1
        ]
    )
    reviews_data2 = "\n".join(
        [
            f"[제품2 리뷰]: {doc.page_content}\n[메타데이터]: {doc.metadata}"
            for doc in docs2
        ]
    )
    products_data = "\n".join(
        [f"[제품 정보]: {row.to_dict()}" for _, row in products_df.iterrows()]
    )

    final_context = f"{reviews_data1}\n\n{reviews_data2}\n\n{products_data}"

    print("분석 방법 : vector")
    return {"context": final_context}
