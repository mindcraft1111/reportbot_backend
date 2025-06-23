import json
import os
import re

import pandas as pd
from dotenv import load_dotenv
from langchain.embeddings.base import Embeddings
from langchain.output_parsers import PydanticOutputParser
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
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

from .parser_classes import PARSER_REGISTRY
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
# r_6_1_2, r_6_1_3 그래프 함수
# ==========================================================================================
# 경쟁사의 reviews 컬럼에서 가장 자주 등장하는 단어들을 반환 
import pandas as pd
from collections import Counter
import re

def get_top_words_in_reviews(product_id1, product_id2, top_n=7, min_length=2):
    stopwords = {
                '이', '그', '저', '것', '거', '이것', '그것', '저것', '그런', '이런', '저런',
                '의', '를', '을', '에', '가', '과', '와', '도', '는', '은', '이다', '다', '하다',
                '있다', '없다', '되다', '아니다', '같다', '다른', '또', '더', '매우', '정말',
                '진짜', '너무', '조금', '많이', '잘', '못', '안', '않', '하지', '해서', '해도',
                '하면', '하고', '하는', '한', '할', '함', '했', '해', '합니다', '입니다', '좋네요',
                '있습니다', '없습니다', '됩니다', '좋습니다', '젠하이저', '한고연몰', '구매했어요',
                '브라운', '신지모루', '그냥', '좀', '약간', '좋고', '디자인도', '믿고', '쓰는'
                '같아요', '헤드폰', '모래', '청소기', '물티슈', '거치대', '같습니다', '있어요',
                '이제', '지금', '오늘', '어제', '내일', '때문', '때문에', '그래서', '그러나',
                '하지만', '그리고', '또한', '역시', '물론', '당연히', '확실히', '아마', '아직',
                '벌써', '이미', '드디어', '마침내', '계속', '항상', '가끔', '때때로', '자주',
                '거의', '전혀', '완전', '상당히', '꽤', '상당', '전체', '부분', '일부', '나머지',
                '다음', '이전', '처음', '마지막', '중간', '사이', '앞', '뒤', '위', '아래', '쓰는',
                '내', '외', '안', '밖', '쪽', '편', '면', '부', '곳', '데', '바', '채', '개', '물티슈는', '아기',
                '번', '회', '차', '도', '등', '같은', '다른', '새로운', '오래된', '큰', '작은', '배송',
                '높은', '낮은', '빠른', '느린', '강한', '좋은', '나쁜', '맞는', '틀린', '흡입력도', 
                '있어요', '쓰고', '감사합니다', '아메솔', '있습니다', '먼지가', '좋아서',' 사용하고',
                '음질도', '음질은', '흡입력이', '있어서', '디베아', '차이슨', '생각보다', '청소기가', '아주', '같아요'
            }

    df1 = pd.read_csv(f"./csv/{product_id1}.csv", encoding='UTF-8')
    df2 = pd.read_csv(f"./csv/{product_id2}.csv", encoding='UTF-8')

    len_df1_reviews = df1['INFO'].dropna().shape[0]
    len_df2_reviews = df2['INFO'].dropna().shape[0]

    # 더 적은 리뷰 수를 `low_review_count` 변수에 저장
    low_review_count = min(len_df1_reviews, len_df2_reviews)

    # 각 데이터프레임에서 `low_review_count` 만큼의 리뷰만 샘플링
    reviews_text1_sampled = df1['INFO'].dropna().sample(n=low_review_count, random_state=1).astype(str)
    reviews_text2_sampled = df2['INFO'].dropna().sample(n=low_review_count, random_state=1).astype(str)

    all_text1 = ' '.join(reviews_text1_sampled).lower()
    all_text2 = ' '.join(reviews_text2_sampled).lower()

    words2 = re.findall(r'[a-zA-Z가-힣0-9]+', all_text2)
    words2 = [word for word in words2 if len(word) >= min_length and word not in stopwords]
    word_counts2 = Counter(words2)
    top_words2 = word_counts2.most_common(top_n)

    top_keywords = [word for word, count in top_words2]
    counts_in_product1 = []
    counts_in_product2 = []

    for keyword in top_keywords:
        #pattern = r'\b' + re.escape(keyword) + r'\b'
        pattern = re.escape(keyword)
        count1 = int(len(re.findall(pattern, all_text1)))
        counts_in_product1.append(count1)

        count2 = int(len(re.findall(pattern, all_text2)))
        counts_in_product2.append(count2)

    result = {
        "r_6_1_1": top_keywords,
        "r_6_1_2": counts_in_product1,
        "r_6_1_3": counts_in_product2
    }
    print(result)

    return result

def get_review_counts_by_year(product1_id: int, product2_id: int):
    from langchain_experimental.agents.agent_toolkits import create_csv_agent
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    """
    두 제품의 2023년, 2024년 리뷰 개수를 에이전트를 통해 추출하고,
    자사 희망 리뷰 수를 LLM에게 요청하여 프론트엔드 형식에 맞춰 반환합니다.

    Args:
        product1_id (int): 자사 제품의 CSV 파일명 (확장자 제외)
        product2_id (int): 경쟁사 제품의 CSV 파일명 (확장자 제외)

    Returns:
        dict: 프론트엔드가 요구하는 형식의 json 데이터 (r_12_1_1, r_12_1_2, r_12_1_3)
              r_12_1_1: [자사 2023년 리뷰수, 자사 2024년 리뷰수, 자사 2025년 리뷰수 목표치]
              r_12_1_2: [경쟁사 2023년 리뷰수, 경쟁사 2024년 리뷰수, 경쟁사 2025년 리뷰수 목표치]
    """

    # 에이전트 생성 도우미 함수 (코드 중복 방지)
    def create_agent_for_product(llm_model, product_id):
        csv_file_path = f"./csv/{product_id}.csv"
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"오류: CSV 파일 '{csv_file_path}'을(를) 찾을 수 없습니다.")

        print(f"'{product_id}.csv' 파일을 기반으로 에이전트를 생성 중입니다...")
        agent = create_csv_agent(
            llm_model,
            csv_file_path,
            verbose=True, # 디버깅을 위해 True 유지
            allow_dangerous_code=True
        )
        print(f"'{product_id}.csv' 에이전트 생성 완료.")
        return agent

    # LLM 응답에서 2023년, 2024년 리뷰 개수 및 예상치 파싱 함수
    def parse_llm_response(agent_response: str) -> tuple[int, int, int]:
        count_2023 = 0
        count_2024 = 0
        target_reviews = 0 # 예상치 기본값 0

        # 2023년 리뷰 개수 추출
        match_2023 = re.search(r'2023년 리뷰 개수:\s*(\d+)', agent_response)
        if match_2023:
            count_2023 = int(match_2023.group(1))

        # 2024년 리뷰 개수 추출
        match_2024 = re.search(r'2024년 리뷰 개수:\s*(\d+)', agent_response)
        if match_2024:
            count_2024 = int(match_2024.group(1))

        # 희망 리뷰 수 추출 (LLM이 '희망 리뷰 수'라고 명시적으로 응답할 경우)
        match_target = re.search(r'(희망 리뷰 수|예상 리뷰 수):\s*(\d+)', agent_response)
        if match_target:
            target_reviews = int(match_target.group(2))
        else:
            # LLM이 예상 리뷰 수를 명시적으로 말해주지 않아도, 2024년 수치 기반으로 계산
            # 이 로직은 LLM의 예측이 아닌, 우리가 설정한 30% 증가 로직입니다.
            target_reviews = int(count_2024 * 1.3) # 30% 증가

        return count_2023, count_2024, target_reviews

    # --- 자사 제품 에이전트 실행 ---
    try:
        self_agent = create_agent_for_product(llm, product1_id)
        # LLM에게 30% 증가한 예상 리뷰 수를 계산해달라고 명확히 지시
        self_query = (
            "전체 리뷰 중 '날짜' 컬럼을 기준으로 2023년도와 2024년도 리뷰의 갯수를 세어서 출력해줘. "
            "그리고 2024년 리뷰 개수에서 30% 증가한 값을 예상 리뷰 수로 제안해줘. "
            "답변은 '2023년 리뷰 개수: [숫자]개, 2024년 리뷰 개수: [숫자]개, 예상 리뷰 수: [숫자]개' 형식으로 해줘."
        )
        print(f"\n자사 에이전트 질문: {self_query}")
        self_response = self_agent.run(self_query)
        print(f"자사 에이전트 답변: {self_response}")
        self_2023_count, self_2024_count, self_target = parse_llm_response(self_response)
    except Exception as e:
        print(f"자사 제품 데이터 처리 중 오류 발생: {e}")
        self_2023_count, self_2024_count, self_target = 0, 0, 0 # 오류 시 기본값

    # --- 경쟁사 제품 에이전트 실행 ---
    competitor_2023_count, competitor_2024_count, competitor_target = 0, 0, 0 # 기본값 초기화
    try:
        competitor_agent = create_agent_for_product(llm, product2_id)
        # 경쟁사 LLM에게도 30% 증가한 예상 리뷰 수를 계산해달라고 명확히 지시
        competitor_query = (
            "전체 리뷰 중 '날짜' 컬럼을 기준으로 2023년도와 2024년도 리뷰의 갯수를 세어서 출력해줘. "
            "그리고 2024년 리뷰 개수에서 30% 증가한 값을 예상 리뷰 수로 제안해줘. "
            "답변은 '2023년 리뷰 개수: [숫자]개, 2024년 리뷰 개수: [숫자]개, 희망 리뷰 수: [숫자]개' 형식으로 해줘."
        )
        print(f"\n경쟁사 에이전트 질문: {competitor_query}")
        competitor_response = competitor_agent.run(competitor_query)
        print(f"경쟁사 에이전트 답변: {competitor_response}")
        competitor_2023_count, competitor_2024_count, competitor_target = parse_llm_response(competitor_response)
    except Exception as e:
        print(f"경쟁사 제품 데이터 처리 중 오류 발생: {e}")

    result = {
        "r_12_1_1": [self_2023_count, self_2024_count, self_target],
        "r_12_1_2": [competitor_2023_count, competitor_2024_count, competitor_target]
    }

    print("\n--- 최종 반환 결과 ---")
    print(result)
    return result

# ==========================================================================================
# 실제 응답처리
# ==========================================================================================
# gemini모델 생성
gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

class GeminiTestView(APIView):
    def post(self, request):
        # ─────────────────────────────────────────────────────────
        # 1단계: 입력 데이터 가져오기
        # ─────────────────────────────────────────────────────────
        user_prompt = request.data.get("user_prompt", "")
        prompt_code = request.data.get("prompt_code", "")
        product_category = request.data.get("product_category", "")
        target_output_format = request.data.get("target_output_format", "")
        product1 = request.data.get("product1", "")
        product2 = request.data.get("product2", "")
        retriever_keyword = request.data.get("retriever_keyword", "")
        # ─────────────────────────────────────────────────────────
        # 2단계: 특정 프롬프트 코드 처리 (예: 투표 그래프)
        # ─────────────────────────────────────────────────────────
        if prompt_code == "C041":
            return Response({"data": vote_graph(prompt_code, product1, 1)})
        if prompt_code == "C051":
            C051_1 = vote_graph(prompt_code, product1, 1)
            C051_2 = vote_graph(prompt_code, product2, 2)
            return Response({"data": C051_2})
        
        if prompt_code == "C061":
            C061 = get_top_words_in_reviews(product1, product2)
            return Response({"data": C061})    

        if prompt_code == "C121":
            C121 = get_review_counts_by_year(product1, product2)
            
            return Response({"data":C121})

        # ─────────────────────────────────────────────────────────
        # 3단계: 제품 데이터 불러오기
        # ─────────────────────────────────────────────────────────
        product1_info = load_product_info(product1)
        product2_info = load_product_info(product2)
        review_data1 = vectordb(product1, True)
        review_data2 = vectordb(product2, True)
        meta_data1 = vectordb(product1, False)
        meta_data2 = vectordb(product2, False)

        # ─────────────────────────────────────────────────────────
        # 키워드 기반 vs. 사용자 프롬프트 기반 검색 조건 분기
        # ─────────────────────────────────────────────────────────
        if retriever_keyword.strip():
            docs1 = review_data1.get_relevant_documents(retriever_keyword)
            docs2 = review_data2.get_relevant_documents(retriever_keyword)
            print(f"✅ retriever_keyword({retriever_keyword})가 제공됐습니다. 벡터스토어 검색에 이 키워드를 사용합니다.")
            print(docs1)
            print(docs2)
        else:
            print("❌ retriever_keyword 제공되지 않았습니다. 벡터스토어 검색에 user_prompt를 사용합니다.")
            docs1 = review_data1.invoke(user_prompt)
            docs2 = review_data2.invoke(user_prompt)
            print(docs1)
            print(docs2)

        # retriever에서 검색한 review 데이터를 json 형태로 serialize
        # 응답에 함께 보내기 위함
        serialized_review_data1 = serialize_documents(docs1)
        serialized_review_data2 = serialize_documents(docs2)

        review_text1 = "\n".join([doc.page_content for doc in docs1])
        review_text2 = "\n".join([doc.page_content for doc in docs2])

        # ─────────────────────────────────────────────────────────
        # 4단계: 토픽 모델링 수행
        # ─────────────────────────────────────────────────────────
        # csvfile = f"./reviews_csv/{product1}.csv"
        # modeler = TopicModeling(
        #     csv_file=csvfile,
        #     extra_stopwords=['잘','거','제가','더','사용','너무','넘','있어요','쓰고','정말','수','정도','있습니다','있는','ㅎㅎ','다','되고','쓸','좋을','듣기','그냥','샀는데','건']
        # )
        # modeler.run()

        # ─────────────────────────────────────────────────────────
        # 5단계: 파서가 없는 경우 기본 응답 처리
        # ─────────────────────────────────────────────────────────
        parser_class = PARSER_REGISTRY.get(prompt_code)

        if not parser_class:
            print(
                f"🙄 {prompt_code} :에 대한 pydantic_output_parser가 존재하지 않습니다. 대신에 target_output_format을 사용하여 계속 진행합니다."
            )

            question = f"""
            요청사항 : {user_prompt}
            자사 데이터 : {product1_info} + {review_text1} + {meta_data1}
            타사 데이터 : {product2_info} + {review_text2} + {meta_data2}
            JSON 응답 구조 : {target_output_format}
            조건 : 현재 제공된 데이터만으로는 이런말 하지말고 요청사항에 대해서만 대답해줘
            """
            response = gemini.invoke(question)
            content = (
                response.content if isinstance(response, AIMessage) else str(response)
            )
            cleaned = clean_markdown(content)

            return Response({"data": cleaned})

            # ─────────────────────────────────────────────────────────
        # 6단계: 파서가 있는 경우 체이닝 및 응답 파싱
        # ─────────────────────────────────────────────────────────
        parser = PydanticOutputParser(pydantic_object=parser_class)
        prompt = PromptTemplate(
            template=""" 
            요청사항 : {user_prompt}
            자사 데이터 : {product1_info} + {review_text1} + {meta_data1}
            타사 데이터 : {product2_info} + {review_text2} + {meta_data2}
            JSON 응답 구조 : {format_instructions}
            조건 : 현재 제공된 데이터만으로는 이런말 하지말고 요청사항에 대해서만 대답해줘
            """,
            input_variables=[
                "user_prompt",
                "product1_info",
                "review_text1",
                "meta_data1",
                "product2_info",
                "review_text2",
                "meta_data2",
            ],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | gemini | parser

        try:
            response = chain.invoke(
                {
                    "user_prompt": user_prompt,
                    "product1_info": product1_info,
                    "review_text1": review_text1,
                    "meta_data1": meta_data1,
                    "product2_info": product2_info,
                    "review_text2": review_text2,
                    "meta_data2": meta_data2,
                }
            )

            try:
                json_data = response.model_dump()
            except AttributeError:
                json_data = response.dict()

            return Response({"data": json_data, "review01": serialized_review_data1, "review02": serialized_review_data2})

        except Exception as e:
            import traceback

            print("⚠️ 체인 실행 또는 유효성 검사 실패:", traceback.format_exc())
            return Response(
                {
                    "error": "AI 응답을 처리하는 도중 오류가 발생했습니다.",
                    "details": str(e),
                    "hint": "프롬프트 응답이 예상된 JSON 구조와 일치하지 않았을 수 있습니다.",
                },
                status=400,
            )


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
    

def serialize_documents(documents):
    return [
        {
            "id": doc.id,
            "metadata": doc.metadata,
            "page_content": doc.page_content
        }
        for doc in documents
    ]
