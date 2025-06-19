import json
import os
import re
import pandas as pd

from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from rest_framework.response import Response
from rest_framework.views import APIView
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine

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
    vectorstore = Chroma(persist_directory=product, embedding_function=embeddings, collection_name=f"reviews_product_{id}")
    if b_retriever == True:
        retriever = vectorstore.as_retriever()
        return retriever
    else :
        metadata = vectorstore._collection.get(include=["metadatas", "documents"])
        metadata_map = {doc: meta for doc, meta in zip(metadata["documents"], metadata["metadatas"])}
        return metadata_map
    
def clean_markdown(text):
    # 코드 블록 (```json ... ```) 제거
    text = re.sub(r"```json\s*(.*?)```", r"\1", text, flags=re.DOTALL)
    # 마크다운 기호 제거
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # 굵은 글씨
    text = re.sub(r"\*(.*?)\*", r"\1", text)       # 기울임 글씨
    text = re.sub(r"#+ ", "", text)                # 제목 표시 ##, ###
    text = text.replace("\\n", "\n")               # 문자열로 인식된 \n을 실제 줄바꿈으로
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
        product1 = request.data.get("product1", "")     # ID
        product1_info = load_product_info(product1)     # 제품
        review_data1 = vectordb(product1, True)         # 리뷰
        meta_data1 = vectordb(product1, False)          # 메타

        # 타사 제품 정보
        product2 = request.data.get("product2", "")     # ID
        product2_info = load_product_info(product2)     # 제품
        review_data2 = vectordb(product2, True)         # 리뷰
        meta_data2 = vectordb(product2, False)          # 메타


        # 문서 추출
        docs1 = review_data1.get_relevant_documents(user_prompt)
        docs2 = review_data2.get_relevant_documents(user_prompt)
        # 텍스트만 추출
        review_text1 = "\n".join([doc.page_content for doc in docs1])
        review_text2 = "\n".join([doc.page_content for doc in docs2])

        # ─────────────────────────────────────────────
        #  일반 질의일 경우: 문서 조합 + 요약 응답
        # ─────────────────────────────────────────────

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

