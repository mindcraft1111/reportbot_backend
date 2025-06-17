from typing_extensions import TypedDict, Optional
from langchain.prompts import PromptTemplate

from langchain_google_genai import ChatGoogleGenerativeAI

import re
import json
import os
import pandas as pd

from langchain_experimental.agents import create_csv_agent
from langchain.agents.agent_types import AgentType
from langgraph.graph import StateGraph, END

from .config import DB_ENGINE
from .tools import vector_analysis, classify_analysis_type

# 현재 junds.py 파일 위치를 기준으로 reviews_csv 디렉토리의 절대경로 생성
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEWS_CSV_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "reviews_csv"))


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
