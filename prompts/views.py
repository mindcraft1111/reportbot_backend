
import os
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
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

# gemini모델 생성
gemini = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)



# ==========================================================================================
# Gemini 응답처리
# ==========================================================================================
class GeminiTestView(APIView):

    def post(self, request):
        # 프롬프트
        user_question = request.data.get("user_prompt", "")
        # 자사 데이터
        review_data1 = vectordb(request.data.get('product1', ''))
        # 타사 데이터
        review_data2 = vectordb(request.data.get("product2", ""))

        # 문서 추출 ([:] 슬라이싱으로 문서 갯수 지정)
        docs1 = review_data1.get_relevant_documents(user_question)[:]
        docs2 = review_data2.get_relevant_documents(user_question)[:]
        # 텍스트만 추출
        review_text1 = "\n".join([doc.page_content for doc in docs1])
        review_text2 = "\n".join([doc.page_content for doc in docs2])


        question = f"""
        요청사항 : {user_question}
        자사 데이터 : {review_text1}
        타사 데이터 : {review_text2}
        조건 : 현재 제공된 데이터만으로는 이런말 하지말고 요청사항에 대해서만 대답해줘
        """
        response = gemini.invoke(question)
        
        if isinstance(response, AIMessage):
            content = response.content
        else:
            content = str(response)

        print("🔥 Gemini 응답 content:", repr(content))

        try:
            parsed = json.loads(content)
            return Response({"data": parsed})
        except json.JSONDecodeError:
            return Response({"data": content})


