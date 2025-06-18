import json
import os
import re

from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from rest_framework.response import Response
from rest_framework.views import APIView
from sentence_transformers import SentenceTransformer

# ==========================================================================================
# 환경 설정
# ==========================================================================================
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

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
def vectordb(id):
    print("제품 id 확인 :", id)
    product = f"./vectordb/reviews/product_{id}"
    vectorstore = Chroma(persist_directory=product, embedding_function=embeddings, collection_name=f"reviews_product_{id}")
    retriever = vectorstore.as_retriever()
    # 디비에서 가져온거 확인
    # results = vectorstore._collection.get(include=["documents"], limit=5)
    # for i, doc in enumerate(results["documents"]):
    #     print(f"[{i+1}] {doc[:200]}...")
    return retriever

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
# 실제 응답처리
# ==========================================================================================

# gemini모델 생성
gemini = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

class GeminiTestView(APIView):

    def post(self, request):
        # 프롬프트
        user_prompt = request.data.get("user_prompt", "")
        # 프롬프트 고유 코드번호
        prompt_code = request.data.get("prompt_code", "")
        # 목표 포맷
        target_output_format = request.data.get("output_format", "")
        # 상품 카테고리
        product_category = request.data.get("product_category", "")
        # 자사 데이터
        review_data1 = vectordb(request.data.get('product1', ''))
        # 타사 데이터
        review_data2 = vectordb(request.data.get("product2", ""))

        # 문서 추출
        docs1 = review_data1.get_relevant_documents(user_prompt)
        docs2 = review_data2.get_relevant_documents(user_prompt)
        # 텍스트만 추출
        review_text1 = "\n".join([doc.page_content for doc in docs1])
        review_text2 = "\n".join([doc.page_content for doc in docs2])

        # 그래프 답변용
        is_graph_request = "그래프" in user_prompt or "시각화" in user_prompt
        # ─────────────────────────────────────────────
        #  그래프 요청일 경우: 벡터DB 문서 추출 + JSON 파싱
        # ─────────────────────────────────────────────
        if is_graph_request:
            
            prompt = f"""
            요청사항: {user_prompt}
            자사 리뷰:
            {review_text1}

            타사 리뷰:
            {review_text2}

            위 데이터를 바탕으로 그래프 시각화를 위한 핵심 수치를 JSON 형식으로 추출해줘.
            예시: {{"category": ["디자인", "성능", "가격"], "my_product": [3.5, 4.1, 2.8], "competitor": [4.2, 4.0, 3.1]}}
            단, 설명 없이 JSON만 반환해줘.
            """

            response = gemini.invoke(prompt)
            content = response.content if isinstance(response, AIMessage) else str(response)
            print("🔥 RAW Gemini 응답:", repr(content))

            # 마크다운 제거
            cleaned = clean_markdown(content)

            try:
                parsed_json = json.loads(cleaned)
                return Response({"graph_data": parsed_json})
            except json.JSONDecodeError:
                return Response({
                    "graph_data": None,
                    "error": "JSON 파싱 실패",
                    "raw_output": cleaned
                })

        # ─────────────────────────────────────────────
        #  일반 질의일 경우: 문서 조합 + 요약 응답
        # ─────────────────────────────────────────────

        question = f"""
        요청사항 : {user_prompt}
        자사 데이터 : {review_text1}
        타사 데이터 : {review_text2}
        조건 : 현재 제공된 데이터만으로는 이런말 하지말고 요청사항에 대해서만 대답해줘
        """

        response = gemini.invoke(question)
        content = response.content if isinstance(response, AIMessage) else str(response)
        cleaned = clean_markdown(content)
        print("Gemini 응답:", cleaned)
        return Response({"data": cleaned})

