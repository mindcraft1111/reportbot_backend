import json
import logging
import os
import traceback

import pandas as pd

################################################################################################
# prompt test
################################################################################################
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from google import genai
from langchain.embeddings.base import Embeddings
from langchain.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine
from typing_extensions import Optional, TypedDict

# =============================================
# GEMINI API KEY 등록
# =============================================
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = api_key

# =============================================
# MySQL 연결 설정
# =============================================
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("SERVER_HOST")
port = "3306"
database = os.getenv("DB_NAME")


# =============================================
# 임베딩 모델 정의
# =============================================
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts):
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def embed_query(self, text):
        return self.model.encode([text], show_progress_bar=False)[0].tolist()


# =============================================
# 상태 정의
# =============================================
class StateDict(TypedDict):
    user_prompt: str
    product1: str
    product2: str
    reviews_data1: Optional[str]
    reviews_data2: Optional[str]
    products_data: Optional[str]
    final_docs: Optional[str]
    context: Optional[str]
    chunk_constraint: Optional[str]
    chunk_type: Optional[str]
    llm_response: Optional[str]
    error: Optional[str]


# =============================================
# Tool 정의 (기능별로 분리)
# =============================================
@tool(description="벡터 데이터베이스에서 제품 리뷰를 검색합니다.")
def search_reviews_vector(product_id: str, user_prompt: str) -> dict:

    if not user_prompt:
        raise ValueError("Prompt is required")  # Django response 말고 예외로 처리
    try:
        # 임베딩 모델 로드 (캐싱 고려)
        embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")
        embeddings = SentenceTransformerEmbeddings(embedding_model)

        # ChromaDB 연결
        vectordb = Chroma(
            persist_directory=f"./vectordb/reviews/product_{product_id}",
            collection_name=f"reviews_product_{product_id}",
            embedding_function=embeddings,
        )

        # 검색 실행
        retriever = vectordb.as_retriever(search_kwargs={"k": 30})
        docs = retriever.invoke(user_prompt)

        # 결과 포맷팅
        reviews_data = "\n".join(
            [
                f"[제품{product_id} 리뷰]: {doc.page_content}\n[메타데이터]: {doc.metadata}"
                for doc in docs
            ]
        )

        return {"success": True, "data": reviews_data, "count": len(docs)}

    except Exception as e:
        logging.error(f"Error searching reviews for product {product_id}: {str(e)}")
        return {"success": False, "error": str(e), "data": ""}

    except Exception as e:
        logging.error(f"Error searching reviews for product {product_id}: {str(e)}")
        return {"success": False, "error": str(e), "data": ""}


@tool(description="MySQL 데이터베이스에서 제품 정보를 조회합니다.")
def get_products_info(product1: str, product2: str) -> dict:
    # MySQL에서 product 정보 로드
    try:
        engine = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        )
        query = f"SELECT * FROM products WHERE id IN ({product1}, {product2})"
        products_df = pd.read_sql(query, con=engine)

        products_data = "\n".join(
            [f"[제품 정보]: {row.to_dict()}" for _, row in products_df.iterrows()]
        )

        return {"success": True, "data": products_data}

    except Exception as e:
        logging.error(f"Error getting product info: {str(e)}")
        return {"success": False, "error": str(e), "data": ""}


# =============================================
# 노드 함수
# =============================================
def load_reviews_node(state: StateDict) -> StateDict:
    """리뷰 데이터 로드 노드"""
    if state.get("error"):
        return state

    user_prompt = state["user_prompt"]
    product1 = state["product1"]
    product2 = state["product2"]

    # search_reviews_vector Tool 사용해서 리뷰 검색
    result1 = search_reviews_vector.invoke(
        {"product_id": product1, "user_prompt": user_prompt}
    )
    result2 = search_reviews_vector.invoke(
        {"product_id": product2, "user_prompt": user_prompt}
    )

    if not result1["success"] or not result2["success"]:
        return {
            **state,
            "error": f"Failed to load reviews: {result1.get('error', '')} {result2.get('error', '')}",
        }

    return {
        **state,  # 딕셔너리 언패킹 후 새로운 데이터 포함
        "reviews_data1": result1["data"],
        "reviews_data2": result2["data"],
    }


def load_products_node(state: StateDict) -> StateDict:
    """제품 정보 로드 노드"""
    if state.get("error"):
        return state

    product1 = state["product1"]
    product2 = state["product2"]

    # Tool 사용해서 제품 정보 조회
    result = get_products_info.invoke({"product1": product1, "product2": product2})

    if not result["success"]:
        return {
            **state,
            "error": f"Failed to load product info: {result.get('error', '')}",
        }

    return {**state, "products_data": result["data"]}


def combine_data_node(state: StateDict) -> StateDict:
    """데이터를 결합하는 노드"""
    if state.get("error"):
        return state

    reviews_data1 = state.get("reviews_data1", "")
    reviews_data2 = state.get("reviews_data2", "")
    products_data = state.get("products_data", "")
    chunk_constraint = state.get("chunk_constraint", "")
    chunk_type = state.get("chunk_type", "")

    final_docs = f"{reviews_data1}\n\n{reviews_data2}\n\n{products_data}\n\n{chunk_constraint}\n\n{chunk_type}"

    return {
        **state,
        "final_docs": final_docs,
        "context": state["user_prompt"],
        "chunk_constraint": state["chunk_constraint"],
    }


# =============================================
# 조건부 엣지 함수
# =============================================
def check_error(state: StateDict) -> str:
    """에러 상태 확인"""
    if state.get("error"):
        return "error"
    return "continue"


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
        "load_reviews", check_error, {"error": END, "continue": "load_products"}
    )

    workflow.add_conditional_edges(
        "load_products", check_error, {"error": END, "continue": "combine_data"}
    )

    workflow.add_edge("combine_data", END)

    return workflow.compile()


# =============================================
# 전역 변수로 그래프 생성
# =============================================
app = create_data_processing_graph()

# =============================================
# Django view
# =============================================


@csrf_exempt
def gemini_non_streaming_mjylove26(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        body = json.loads(request.body)
        user_prompt = body.get("user_prompt", "").strip()
        product1 = body.get("product1", "").strip()
        product2 = body.get("product2", "").strip()
        chunk_constraint = body.get("chunk_constraint")
        chunk_type = body.get("chunk_type")

        if not user_prompt:
            return JsonResponse({"error": "Prompt is required"}, status=400)

        state = {
            "user_prompt": user_prompt,
            "product1": product1,
            "product2": product2,
            "chunk_constraint": chunk_constraint,
            "chunk_type": chunk_type,
            "reviews_data1": None,
            "reviews_data2": None,
            "products_data": None,
            "final_docs": None,
            "context": None,
            "llm_response": None,
            "error": None,
        }

        # LangGraph 실행
        result = app.invoke(state)

        if result.get("error"):
            return JsonResponse({"error": result["error"]}, status=400)

        final_docs = result["final_docs"]
        user_prompt = result["context"]

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """너는 두 제품의 리뷰 데이터를 비교하고 분석하는 데이터 분석 전문가야. 
                    타사 제품 대비 자사 제품의 장단점을 파악하고 개선점을 찾기 위해 
                    그에 맞는 리포트 내부 텍스트를 작성하는 서비스를 제공 해줘.
                    product1은 자사 제품이고, product2는 경쟁사 제품이야.
                    chunk_constraint는 전송해야 할 json 예시이며, 답변은 무조건 설명 혹은 텍스트를 제외한 json 형식으로만 해야 해.
                    key값과 그 구조는 무조건 chunk_constraint와 동일하게 하고 value값만 변경하여 같은 json 형식으로 출력해줘야해.

                    제한된 토큰 안에서 내용이 부정확하거나 답변이 끊기는 등 제품 관련 질문에 대한 답변이 모호해지면 안돼.
                    답변은 한국어로 작성해주고, 모르는 내용은 모른다고 답해줘.""",
                ),
                ("user", "요청: {user_prompt}\n\nContext:\n{final_docs}"),
            ]
        )

        formatted_prompt = prompt.format(user_prompt=user_prompt, final_docs=final_docs)

        # Gemini API (non-streaming)
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=formatted_prompt,
        )

        full_text = response.text if hasattr(response, "text") else str(response)

        return JsonResponse({"text": full_text}, status=200)

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return JsonResponse({"error": f"Exception occurred: {str(e)}"}, status=500)
