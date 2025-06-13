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

from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import numpy as np

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


class StateDict(TypedDict):
    user_prompt: str
    product1: str
    product2: str
    docs: Optional[str]
    context: Optional[str]
    llm_response: Optional[str]


@tool(description="리뷰 및 제품 데이터를 로드하고 context를 생성합니다.")
def load_data(user_prompt: str, product1: str, product2: str) -> dict:

    if not user_prompt:
        raise ValueError("Prompt is required")  # Django response 말고 예외로 처리

    # 임베딩 모델 로드
    embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")
    embeddings = SentenceTransformerEmbeddings(embedding_model)

    # 두 개의 ChromaDB 불러오기
    vectordb1 = Chroma(
        persist_directory=f"./vectordb/reviews/product_{product1}",
        collection_name=f"reviews_product_{product1}",
        embedding_function=embeddings,
    )
    vectordb2 = Chroma(
        persist_directory=f"./vectordb/reviews/product_{product2}",
        collection_name=f"reviews_product_{product2}",
        embedding_function=embeddings,
    )

    # retriever 거리 기반 리뷰 검색
    retriever1 = vectordb1.as_retriever(search_kwargs={"k": 30})
    retriever2 = vectordb2.as_retriever(search_kwargs={"k": 30})

    # MySQL에서 product 정보 로드
    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    )
    query = f"SELECT * FROM products WHERE id IN ({product1}, {product2})"
    products_df = pd.read_sql(query, con=engine)

    # retriever로 context (리뷰)만 받음
    docs1 = retriever1.invoke(user_prompt)
    docs2 = retriever2.invoke(user_prompt)

    # context: 리뷰 + 별도로 불러온 메타데이터를 조합
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

    final_docs = f"{reviews_data1}\n\n{reviews_data2}\n\n{products_data}"

    return {"docs": final_docs, "context": user_prompt}


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

        state = {
            "user_prompt": user_prompt,
            "product1": product1,
            "product2": product2,
            "docs": None,
            "context": None,
            "llm_response": None,
        }

        result = app.invoke(state)  # LangGraph 실행

        final_docs = result["docs"]
        user_prompt = result["context"]

    except Exception as e:
        import traceback, sys

        traceback.print_exc(file=sys.stderr)
        return JsonResponse({"error": f"Invalid input: {str(e)}"}, status=400)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """너는 두 제품의 리뷰 데이터를 비교하고 분석하는 데이터 분석 전문가야. 
                        타사 제품 대비 자사 제품의 장단점을 파악하고 개선점을 찾기 위해 
                        그에 맞는 리포트 내부 텍스트를 작성하는 서비스를 제공 해줘.
                        product1은 자사 제품이고, product2는 경쟁사 제품이야.

                        제한된 토큰 안에서 내용이 부정확하거나 답변이 끊기는 등 제품 관련 질문에 대한 답변이 모호해지면 안돼.
                        답변은 한국어로 작성해주고, 모르는 내용은 모른다고 답해줘.""",
            ),
            ("user", "요청: {user_prompt}\n\nContext:\n{final_docs}"),
        ]
    )

    formatted_prompt = prompt.format(user_prompt=user_prompt, final_docs=final_docs)

    model_agent = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

    import pandas as pd

    # product1_agent = create_csv_agent(
    #     model_agent,
    #     f"./review_csv/{product1}.csv",
    #     verbose=True,
    #     allow_dangerous_code=True,
    # )
    try:
        answer = product1_agent.run(user_prompt)  # 또는 invoke({...})
    except Exception as e:
        answer = f"에이전트 실행 중 오류: {e}"

    # Gemini API
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    stream = client.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=formatted_prompt,
        # eneration_config={
        # max_output_tokens":state["input"]["max_tokens"]
        #
    )

    def gen():
        # if type in "graph":
        # try:
        #     yield f"data: {json.dumps({'text': answer})}\n\n"
        # except Exception as e:
        #     yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # else:
        try:
            for chunk in stream:
                # Check if chunk has text content
                if hasattr(chunk, "text") and chunk.text:
                    print(f"Sending chunk: {chunk.text[:50]}...")  # Debug print
                    # Wrap with SSE format
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        except Exception as e:
            print(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingHttpResponse(
        gen(),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


builder = StateGraph(StateDict)
builder.add_node("load_data", load_data)
builder.set_entry_point("load_data")
builder.set_finish_point("load_data")
app = builder.compile()
