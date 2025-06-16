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
from langchain.prompts import ChatPromptTemplate, PromptTemplate

from sqlalchemy import create_engine
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from langchain.embeddings.base import Embeddings

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda
from typing_extensions import TypedDict, Optional

from langchain_experimental.agents import create_csv_agent
from langchain.agents.agent_types import AgentType

import re

# 현재 junds.py 파일 위치를 기준으로 reviews_csv 디렉토리의 절대경로 생성
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEWS_CSV_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "reviews_csv"))

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

DB_ENGINE = create_engine(
    f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
)


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
class AnalysisState(TypedDict):
    user_prompt: str
    product1: str
    product2: str
    analysis_type: Optional[str]  # 'vector' 또는 'metrics'
    target: Optional[str]  # 'own', 'comp', 'both'
    context: Optional[str]
    llm_response: Optional[str]


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


# =============================================
# 메트릭 분석 노드들
# =============================================
def classify_target_node(state: AnalysisState) -> AnalysisState:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    classification_prompt = PromptTemplate.from_template(
        """
        다음 문장을 읽고, 자사/경쟁사/자사+경쟁사 중 어떤 데이터를 기반으로 질문한 것인지 판단해줘.
        - 자사만: own
        - 경쟁사만: comp
        - 둘 다 포함: both
        다음 형식으로만 JSON 응답해줘:
        ```json
        {{
        "data_source": "own" | "comp" | "both",
        "reason": "간단한 설명"
        }}
        ```

        문장: {prompt}
        답:
        """
    )
    prompt_text = state.get("user_prompt", "").strip()
    result = llm.invoke(classification_prompt.format(prompt=prompt_text))
    content = result.content.strip()
    try:
        json_text = re.sub(r"^```json\s*|```$", "", content).strip()
        parsed = json.loads(json_text)
        print("분석 방법 : metrics")
        return {
            **state,
            "target": parsed["data_source"],
        }
    except Exception as e:
        return {**state, "target": "both"}  # 기본값


def generate_own_metrics_node(state: AnalysisState) -> AnalysisState:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    csv_path1 = os.path.join(REVIEWS_CSV_DIR, f"{state['product1']}.csv")

    agent = create_csv_agent(
        llm,
        csv_path1,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        allow_dangerous_code=True,
    )

    query = f"SELECT * FROM products WHERE id = {state['product1']}"
    product_df = pd.read_sql(query, con=DB_ENGINE)
    product_info = (
        product_df.to_dict(orient="records")[0] if not product_df.empty else {}
    )

    response = agent.run(state["user_prompt"])
    context = f"{response}\n\n[제품 정보]: {product_info}"
    return {**state, "context": context}


def generate_comp_metrics_node(state: AnalysisState) -> AnalysisState:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    csv_path2 = os.path.join(REVIEWS_CSV_DIR, f"{state['product2']}.csv")

    agent = create_csv_agent(
        llm,
        csv_path2,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        allow_dangerous_code=True,
    )

    query = f"SELECT * FROM products WHERE id = {state['product2']}"
    product_df = pd.read_sql(query, con=DB_ENGINE)
    product_info = (
        product_df.to_dict(orient="records")[0] if not product_df.empty else {}
    )

    response = agent.run(state["user_prompt"])
    context = f"{response}\n\n[제품 정보]: {product_info}"
    return {**state, "context": context}


def generate_both_metrics_node(state: AnalysisState) -> AnalysisState:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    csv_path1 = os.path.join(REVIEWS_CSV_DIR, f"{state['product1']}.csv")
    csv_path2 = os.path.join(REVIEWS_CSV_DIR, f"{state['product2']}.csv")

    agent = create_csv_agent(
        llm,
        [csv_path1, csv_path2],
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        allow_dangerous_code=True,
    )

    query = (
        f"SELECT * FROM products WHERE id IN ({state['product1']}, {state['product2']})"
    )
    product_df = pd.read_sql(query, con=DB_ENGINE)

    # 각각 딕셔너리로 분리
    own_info = product_df[product_df["id"] == int(state["product1"])]
    comp_info = product_df[product_df["id"] == int(state["product2"])]

    own_info_dict = own_info.to_dict(orient="records")[0] if not own_info.empty else {}
    comp_info_dict = (
        comp_info.to_dict(orient="records")[0] if not comp_info.empty else {}
    )

    response = agent.run(state["user_prompt"])
    context = (
        f"{response}\n\n"
        f"[자사 제품 정보]: {own_info_dict}\n"
        f"[경쟁사 제품 정보]: {comp_info_dict}"
    )

    return {**state, "context": context}


# =============================================
# 라우팅 함수들
# =============================================
def route_by_analysis_type(state: AnalysisState) -> str:
    analysis_type = state.get("analysis_type")
    if analysis_type == "vector":
        return "vector_analysis"
    elif analysis_type == "metrics":
        return "classify_target"
    else:
        return "vector_analysis"  # 기본값


def route_by_target(state: AnalysisState) -> str:
    target = state.get("target")
    if target not in ["own", "comp", "both"]:
        return "generate_both_metrics"  # 기본값
    return {
        "own": "generate_own_metrics",
        "comp": "generate_comp_metrics",
        "both": "generate_both_metrics",
    }[target]


# =============================================
# 분석 노드들
# =============================================
def classify_analysis_node(state: AnalysisState) -> AnalysisState:
    result = classify_analysis_type.invoke(state["user_prompt"])
    return {**state, "analysis_type": result["analysis_type"]}


def vector_analysis_node(state: AnalysisState) -> AnalysisState:
    result = vector_analysis.invoke(
        {
            "user_prompt": state["user_prompt"],
            "product1": state["product1"],
            "product2": state["product2"],
        }
    )
    return {**state, "context": result["context"]}


# =============================================
# 워크플로우 구성
# =============================================
def create_analysis_workflow():
    workflow = StateGraph(AnalysisState)

    # 노드 추가
    workflow.add_node("classify_analysis", classify_analysis_node)
    workflow.add_node("vector_analysis", vector_analysis_node)
    workflow.add_node("classify_target", classify_target_node)
    workflow.add_node("generate_own_metrics", generate_own_metrics_node)
    workflow.add_node("generate_comp_metrics", generate_comp_metrics_node)
    workflow.add_node("generate_both_metrics", generate_both_metrics_node)

    # 시작점 설정
    workflow.set_entry_point("classify_analysis")

    # 조건부 엣지 추가
    workflow.add_conditional_edges(
        "classify_analysis",
        route_by_analysis_type,
        {
            "vector_analysis": "vector_analysis",
            "classify_target": "classify_target",
        },
    )

    workflow.add_conditional_edges(
        "classify_target",
        route_by_target,
        {
            "generate_own_metrics": "generate_own_metrics",
            "generate_comp_metrics": "generate_comp_metrics",
            "generate_both_metrics": "generate_both_metrics",
        },
    )

    # 종료점 설정
    workflow.set_finish_point("vector_analysis")
    workflow.set_finish_point("generate_own_metrics")
    workflow.set_finish_point("generate_comp_metrics")
    workflow.set_finish_point("generate_both_metrics")

    return workflow.compile()


@csrf_exempt
def gemini_streaming_junds(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        body = json.loads(request.body)
        user_prompt = body.get("user_prompt", "").strip()
        product1 = body.get("product1", "").strip()
        product2 = body.get("product2", "").strip()
        chunk_constraint = body.get("chunk_constraint")
        chunk_type = body.get("chunk_type")

        print("😀😀😀", body)

        if not user_prompt:
            return JsonResponse({"error": "Prompt is required"}, status=400)

        # 초기 상태 설정
        initial_state = {
            "user_prompt": user_prompt,
            "product1": product1,
            "product2": product2,
            "analysis_type": None,
            "target": None,
            "context": None,
            "llm_response": None,
        }

        # 워크플로우 실행
        app = create_analysis_workflow()
        result = app.invoke(initial_state)

        # 결과에서 컨텍스트 추출
        final_context = result.get("context", "데이터가 부족합니다.")

    except Exception as e:
        import traceback, sys

        traceback.print_exc(file=sys.stderr)
        return JsonResponse({"error": f"Invalid input: {str(e)}"}, status=400)
    # 프롬프트 템플릿 구성
    full_prompt = f"""# 역할 정의
당신은 리뷰 데이터 분석 전문가입니다. 제공된 Context 데이터만을 사용하여 정확한 분석을 수행해야 합니다.

# 핵심 규칙 (절대 위반 금지)
1. **데이터 무결성**: 제공된 Context에 없는 수치나 정보는 절대 생성하지 마세요
2. **정확성 우선**: 불확실하면 "데이터 부족으로 확인 불가"라고 명시하세요
3. **추정 금지**: "약", "대략", "추정" 등의 표현으로 임의 수치 제시 금지
4. **사실 기반**: Context에서 직접 확인할 수 있는 내용만 언급하세요

# 분석 지침
- product1: 자사 제품
- product2: 경쟁사 제품
- 비교 분석 시 구체적인 근거와 수치를 Context에서 인용하세요
- 개선점 제안 시에도 데이터 기반으로만 제안하세요

# 응답 형식
입력 받은 prompt 의 예시대로 JSON으로 응답

# 사용자 요청
{user_prompt}

# Context 데이터
```
{final_context}
```

# 응답 요구사항
- 한국어로 응답
- Context에 없는 정보는 "해당 데이터 없음" 또는 "Context에서 확인 불가"로 표시
- 수치나 통계는 Context에서 직접 인용한 것만 사용
- 분석이 불가능한 경우 그 이유를 명확히 설명

# 금지 사항 (절대 하지 말 것)
❌ 임의의 수치나 퍼센트 생성
❌ "일반적으로", "보통", "평균적으로" 등의 추정 표현
❌ Context에 없는 제품 특성이나 기능 언급
❌ 가상의 시나리오나 예시 생성
❌ 불확실한 정보에 대한 추측성 답변

✅ Context에서 직접 확인되는 정보만 사용
✅ 데이터 부족 시 명확한 한계 표시
✅ 근거 있는 분석과 제안만 제공

다음 질문에 대해 반드시 CSV 데이터에서만 확인된 수치로만 답하세요. 임의로 숫자를 추정하거나 생성하지 마세요.
데이터가 없으면 "해당 데이터 없음"이라고 명시하세요.
위 규칙을 엄격히 준수하여 응답해주세요."""

    # Gemini API
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    stream = client.models.generate_content_stream(
        model="gemini-2.0-flash",
        contents=[{"parts": [{"text": full_prompt}]}],
        # eneration_config={
        # max_output_tokens":state["input"]["max_tokens"]
        #
    )

    def gen():
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
