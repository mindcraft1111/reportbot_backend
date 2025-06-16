from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UpdateUserSerializer,
)

from .models import Users


class RegisterView(
    generics.CreateAPIView
):  # 회원가입 CreateAPIView는 POST 요청을 처리하기 때문에 따로 post() 메서드를 정의할 필요가 없습니다.
    queryset = Users.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    # 디버깅용
    def perform_create(self, serializer):
        print(
            "🔥 perform_create() 호출됨 - serializer.validated_data:",
            serializer.validated_data,
        )
        serializer.save()


"""
로그아웃은 프론트에서 Refresh 토큰을 보내면 서버에서 Refresh 토큰을 블랙리스트 처리만
로그인 하면 클라이언트는 두개의 토큰 모두저장함
프론트에서 보내주면 자체적으로 처리
* 프론트는 가능한 경우 Refresh 토큰을 HttpOnly Cookie에 저장하는 것이 안전
"""


class LogoutView(APIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]  # 프론트에서 바디에 refresh있어야함 ( "refresh" : "리프레쉐 토큰")

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "로그아웃"}, status=204)
        except TokenError as e:
            return Response({"detail": str(e)}, status=400)
        except Exception:
            return Response({"detail": "Invalid request."}, status=400)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class DeleteUserView(APIView):  # 프론트에서 헤더에 access_token있어야함
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response(
            {"detail": "회원 탈퇴가 완료되었습니다."}, status=status.HTTP_204_NO_CONTENT
        )


class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]  # 프론트에서 헤더에 access_token있어야함

    def put(self, request):
        user = request.user  # 현재 로그인한 사용자 가져오기
        serializer = UpdateUserSerializer(
            user, data=request.data, partial=True
        )  # partial=True로 하면 일부만 수정 가능
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "회원정보가 성공적으로 수정되었습니다."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

################################################################################################
# prompt test
################################################################################################
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from google import genai
from django.views.decorators.csrf import csrf_exempt
import json

import os
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

from sqlalchemy import create_engine
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from langchain.embeddings.base import Embeddings

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda
from typing_extensions import TypedDict, Optional
import logging

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
    llm_response: Optional[str]
    error: Optional[str]

# =============================================
# Tool 정의 (기능별로 분리)
# =============================================
@tool(description="벡터 데이터베이스에서 제품 리뷰를 검색합니다.")
def search_reviews_vector(product_id: str, user_prompt:str)-> dict:
     
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
            embedding_function=embeddings
        )

        # 검색 실행
        retriever = vectordb.as_retriever(search_kwargs={"k": 30})
        docs = retriever.invoke(user_prompt)

        # 결과 포맷팅
        reviews_data = "\n".join([
            f"[제품{product_id} 리뷰]: {doc.page_content}\n[메타데이터]: {doc.metadata}" 
            for doc in docs
        ])

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
    
@tool(description="MySQL 데이터베이스에서 제품 정보를 조회합니다.")
def get_products_info(product1: str, product2: str)->dict:
    # MySQL에서 product 정보 로드
    try:
        engine = create_engine(
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        )
        query = f"SELECT * FROM products WHERE id IN ({product1}, {product2})"
        products_df = pd.read_sql(query, con=engine)

        products_data = "\n".join([
            f"[제품 정보]: {row.to_dict()}" 
            for _, row in products_df.iterrows()
        ])

        return {
            "success": True,
            "data": products_data
        }

    except Exception as e:
        logging.error(f"Error getting product info: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": ""
        }
    
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
    result1 = search_reviews_vector.invoke({"product_id": product1, "user_prompt": user_prompt})
    result2 = search_reviews_vector.invoke({"product_id": product2, "user_prompt": user_prompt})
    
    if not result1["success"] or not result2["success"]:
        return {
            **state,
            "error": f"Failed to load reviews: {result1.get('error', '')} {result2.get('error', '')}"
        }
    
    return {
        **state, # 딕셔너리 언패킹 후 새로운 데이터 포함
        "reviews_data1": result1["data"],
        "reviews_data2": result2["data"]
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
            "error": f"Failed to load product info: {result.get('error', '')}"
        }
    
    return {
        **state,
        "products_data": result["data"]
    }

def combine_data_node(state: StateDict) -> StateDict:
    """데이터를 결합하는 노드"""
    if state.get("error"):
        return state
    
    reviews_data1 = state.get("reviews_data1", "")
    reviews_data2 = state.get("reviews_data2", "")
    products_data = state.get("products_data", "")
    
    final_docs = f"{reviews_data1}\n\n{reviews_data2}\n\n{products_data}"
    
    return {
        **state,
        "final_docs": final_docs,
        "context": state["user_prompt"]
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

# =============================================
# 전역 변수로 그래프 생성
# =============================================
app = create_data_processing_graph()

# =============================================
# Django view
# =============================================
@csrf_exempt
def gemini_streaming(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        body = json.loads(request.body)
        user_prompt = body.get("user_prompt", "").strip()
        product1 = body.get("product1", "").strip()
        product2 = body.get("product2", "").strip()

        if not user_prompt:
            return JsonResponse({"error": "Prompt is required"}, status=400)

        # 초기 상태 설정
        state = {
            "user_prompt": user_prompt,
            "product1": product1,
            "product2": product2,
            "reviews_data1": None,
            "reviews_data2": None,
            "products_data": None,
            "final_docs": None,
            "context": None,
            "llm_response": None,
            "error": None
        }

        # LangGraph 실행
        result = app.invoke(state)  

        if result.get("error"):
            return JsonResponse({"error": result["error"]}, statue=4000)
        
        final_docs = result["final_docs"]
        user_prompt = result["context"]

    except Exception as e:
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        return JsonResponse({"error": f"Invalid input: {str(e)}"}, status=400)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """너는 두 제품의 리뷰 데이터를 비교하고 분석하는 데이터 분석 전문가야. 
            타사 제품 대비 자사 제품의 장단점을 파악하고 개선점을 찾기 위해 
            그에 맞는 리포트 내부 텍스트를 작성하는 서비스를 제공 해줘.
            product1은 자사 제품이고, product2는 경쟁사 제품이야.

            제한된 토큰 안에서 내용이 부정확하거나 답변이 끊기는 등 제품 관련 질문에 대한 답변이 모호해지면 안돼.
            답변은 한국어로 작성해주고, 모르는 내용은 모른다고 답해줘."""
        ),
        ("user", "요청: {user_prompt}\n\nContext:\n{final_docs}")
    ])

    formatted_prompt = prompt.format(
        user_prompt=user_prompt,
        final_docs=final_docs
    )
    
    # Gemini API
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    stream = client.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=formatted_prompt,
        #eneration_config={
        #max_output_tokens":state["input"]["max_tokens"]
        #
    )

    def gen():
        try:
            for chunk in stream:
                # Check if chunk has text content
                if hasattr(chunk, 'text') and chunk.text:
                    print(f"Sending chunk: {chunk.text[:50]}...")  # Debug print
                    # Wrap with SSE format
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        except Exception as e:
            print(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingHttpResponse(
        gen(),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
