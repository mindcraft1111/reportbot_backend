import json
import os
import re

import pandas as pd
from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine

from api.models import Prompt, PromptTest
from api.models.utils.response import api_response

from .serializers import (
    PromptCreateSerializer,
    PromptSerializer,
    PromptTestCreateSerializer,
    PromptTestSerializer,
)

from .topicModeling import TopicModeling
# ==========================================================================================
# 환경 설정
# ==========================================================================================
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# =============================================
# MySQL 연결 설정
# =============================================
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("SERVER_HOST")
port = "3306"
database = os.getenv("DB_NAME")


# ==========================================================================================
# 임베딩 모델 설정
# ==========================================================================================
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts):
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def embed_query(self, text):
        return self.model.encode([text], show_progress_bar=False)[0].tolist()


embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")
embeddings = SentenceTransformerEmbeddings(embedding_model)


# ==========================================================================================
# 벡터DB 로딩 함수
# ==========================================================================================
def vectordb(id, b_retriever):
    print("제품 id 확인 :", id)
    product = f"./vectordb/reviews/product_{id}"
    vectorstore = Chroma(
        persist_directory=product,
        embedding_function=embeddings,
        collection_name=f"reviews_product_{id}",
    )
    if b_retriever == True:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 30})
        return retriever
    else:
        metadata = vectorstore._collection.get(include=["metadatas", "documents"])
        metadata_map = {
            doc: meta for doc, meta in zip(metadata["documents"], metadata["metadatas"])
        }
        return metadata_map


def clean_markdown(text):
    # 코드 블록 (```json ... ```) 제거
    text = re.sub(r"```json\s*(.*?)```", r"\1", text, flags=re.DOTALL)
    # 마크다운 기호 제거
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # 굵은 글씨
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # 기울임 글씨
    text = re.sub(r"#+ ", "", text)  # 제목 표시 ##, ###
    text = text.replace("\\n", "\n")  # 문자열로 인식된 \n을 실제 줄바꿈으로
    return text.strip()


# ==========================================================================================
# MySQL에서 product 정보 로드
# ==========================================================================================
def load_product_info(product_id):
    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    )
    query = f"SELECT * FROM products WHERE id IN ({product_id})"
    products_df = pd.read_sql(query, con=engine)

    return products_df


# ==========================================================================================
# r_4_1, r_5_2 그래프 총 별점 기반 긍부정 분석
# ==========================================================================================
def vote_graph(prompt_code, product_id, id):
    global positive_percentages, negative_percentages
    df = pd.read_csv(f"./csv/{product_id}.csv")

    # 2. '부정' (1, 2)과 '긍정' (4, 5)으로 분류
    negative_votes = df[df["VOTE"].isin([1, 2])].shape[0]
    positive_votes = df[df["VOTE"].isin([4, 5])].shape[0]

    # 총 유효 투표 수
    total_valid_votes = negative_votes + positive_votes

    # 3. 비율 계산 (퍼센트)
    if total_valid_votes > 0:
        negative_percentage = (negative_votes / total_valid_votes) * 100
        positive_percentage = (positive_votes / total_valid_votes) * 100
    else:
        negative_percentage = 0.0
        positive_percentage = 0.0

    if prompt_code == "C041":
        result = {
            "r_4_1_1": f"{positive_percentage:.1f}",
            "r_4_1_2": f"{negative_percentage:.1f}",
        }
        return result

    if prompt_code == "C051":
        if id == 1:
            positive_percentages = [f"{positive_percentage:.1f}"]
            negative_percentages = [f"{negative_percentage:.1f}"]
            return 0
        if id == 2:
            positive_percentages.append(f"{positive_percentage:.1f}")
            negative_percentages.append(f"{negative_percentage:.1f}")

            result = {"r_5_2_1": positive_percentages, "r_5_2_2": negative_percentages}
            return result


# ==========================================================================================
# 그래프용 csv load
# ==========================================================================================
def load_keyword_csv(product_id):
    df = pd.read_csv(f"./csv/keyword_analysis_product_{product_id}.csv")
    return df


# ==========================================================================================
# 실제 응답처리
# ==========================================================================================


# gemini모델 생성
gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)


class GeminiTestView(APIView):

    def post(self, request):

        # 프롬프트
        user_prompt = request.data.get("user_prompt", "")
        # 프롬프트 고유 코드번호
        prompt_code = request.data.get("prompt_code", "")
        # 상품 카테고리
        product_category = request.data.get("product_category", "")
        # JSON 응답 구조 정의
        target_output_format = request.data.get("target_output_format", "")

        # 자사 제품 정보
        product1 = request.data.get("product1", "")  # ID
        product2 = request.data.get("product2", "")  # ID
        if prompt_code == "C041":
            C041 = vote_graph(prompt_code, product1, 1)
            return Response({"data": C041})

        if prompt_code == "C051":
            C051_1 = vote_graph(prompt_code, product1, 1)
            C051_2 = vote_graph(prompt_code, product2, 2)
            return Response({"data": C051_2})

        product1_info = load_product_info(product1)  # 제품
        review_data1 = vectordb(product1, True)  # 리뷰
        meta_data1 = vectordb(product1, False)  # 메타

        product2_info = load_product_info(product2)  # 제품
        review_data2 = vectordb(product2, True)  # 리뷰
        meta_data2 = vectordb(product2, False)  # 메타

        # 문서 추출
        docs1 = review_data1.get_relevant_documents(user_prompt)
        docs2 = review_data2.get_relevant_documents(user_prompt)
        # 텍스트만 추출
        review_text1 = "\n".join([doc.page_content for doc in docs1])
        review_text2 = "\n".join([doc.page_content for doc in docs2])

        # csv파일 가져오기
        csvfile = f"./reviews_csv/{product1}.csv"
        # 토픽 모델링
        custom_stopwords = ['잘', '거', '제가', '더', '사용','너무','넘','있어요','쓰고','정말','쓰고','수','정도','있습니다','있는',
                            'ㅎㅎ','다','되고','쓸','좋을','듣기','그냥','샀는데','건']
        modeler = TopicModeling(
            csv_file = csvfile,
            extra_stopwords=custom_stopwords
        )
        modeler.run()

        # ─────────────────────────────────────────────
        #  일반 질의일 경우: 문서 조합 + 요약 응답
        # ─────────────────────────────────────────────
        #          + {keyword_csv1}
        #  + {keyword_csv2}
        question = f"""
        요청사항 : {user_prompt}
        자사 데이터 : {product1_info} + {review_text1} + {meta_data1}
        타사 데이터 : {product2_info} + {review_text2} + {meta_data2}
        JSON 응답 구조 : {target_output_format}
        조건 : 현재 제공된 데이터만으로는 이런말 하지말고 요청사항에 대해서만 대답해줘
        """

        response = gemini.invoke(question)
        content = response.content if isinstance(response, AIMessage) else str(response)
        cleaned = clean_markdown(content)
        print("Gemini 응답:", cleaned)
        return Response({"data": cleaned})


class PromptViewset(viewsets.ModelViewSet):
    queryset = Prompt.objects.all()
    serializer_class = PromptSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return PromptCreateSerializer

        return PromptSerializer

    @action(detail=False, methods=["post"], url_path="approve-test")
    def approve_test(self, request):
        test_id = request.data.get("id")
        if not test_id:
            return api_response(
                code=-1, msg="테스트 프롬프트 id가 필요합니다.", status_code=400
            )

        try:
            test = PromptTest.objects.get(id=test_id)
        except PromptTest.DoesNotExist:
            return api_response(
                code=-1, msg="해당 테스트가 존재하지 않습니다.", status_code=404
            )

        # PromptTest 기반으로 Prompt 생성
        prompt = Prompt.objects.create(
            category=test.category,
            flag="text",  # 추후 수정
            chunk_code=test.chunk_code,
            prompt_text=test.question,
            response_example=test.answer,
        )

        # passed 처리
        test.passed = True
        test.save(update_fields=["passed"])

        # 응답
        return api_response(
            msg="Prompt로 등록되었습니다.",
            data=PromptSerializer(prompt).data,
            status_code=201,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        print("serializer = ", serializer)
        print("serializer = ", self.get_serializer)
        print("data: ", request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_response(dat=serializer.data, status=201)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)


class PromptTestViewset(viewsets.ModelViewSet):
    queryset = PromptTest.objects.all()
    serializer_class = PromptTestSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "chunk_code"

    def get_serializer_class(self):
        if self.action == "create":
            return PromptTestCreateSerializer
        return PromptTestSerializer

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        prompt_test = create_serializer.save(reviewer=request.user)

        response_serializer = PromptTestSerializer(prompt_test)
        return api_response(data=response_serializer.data, status_code=201)

    @action(detail=False, methods=["get"], url_path="(?P<chunk_code>C[^/.]+)")
    def get_by_chunk_code(self, request, chunk_code=None):
        queryset = self.get_queryset().filter(chunk_code=chunk_code)
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)
