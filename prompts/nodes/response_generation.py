from prompts.llm.gemini import llm
from prompts.state.prompt_state import PromptState
from langchain.prompts import ChatPromptTemplate


# 전체 제약 조건 정리
def get_constraint_description(constraints: dict) -> str:
    lines = []
    for key, spec in constraints.items():
        desc = []
        if spec.max_length:
            desc.append(f"{spec.max_length}자 이하")
        if spec.format:
            desc.append(spec.format)
        lines.append(f"- {key}: {', '.join(desc)}")
    return "\n".join(lines)


def generate_prompt_node(state: PromptState):
    print("✨✨✨ 생성노드 진입 ✨✨✨")

    messages = ChatPromptTemplate.from_messages(
        [
            ("system", """
                너는 두 제품의 리뷰 데이터를 비교하고 분석하는 데이터 분석 전문가야. 
                타사 제품 대비 자사 제품의 장단점을 파악하고 개선점을 찾기 위해 
                그에 맞는 리포트 내부 텍스트를 작성하는 서비스를 제공 해줘.
                product1은 자사 제품이고, product2는 경쟁사 제품이야.

                제한된 토큰 안에서 내용이 부정확하거나 답변이 끊기는 등 제품 관련 질문에 대한 답변이 모호해지면 안돼.
                답변은 한국어로 작성해주고, 모르는 내용은 모른다고 답해줘.

                ❗ 아래 규칙을 반드시 따라야 해:
                - 항목 이름(`r_1_1` 등)은 출력하지 마.
                - 항목 순서를 유지해서 각각의 응답만 출력해. (예: r_1_1 응답 → 줄바꿈 → r_1_2 응답 → ...)
                - 불필요한 설명 없이 텍스트만 출력해.
                - 항목 간 중복 없이 유기적으로 연결된 응답을 작성해.
                - constraint의 **ex) 뒤 내용을 반드시 참고**해.
                - **글자수 제한 조건 반드시 지켜.**
            """
            ),
            (
                "human",
                "요청: {user_prompt}\n\n제약조건: {constraints}\n\nContext:\n{final_docs}",
            ),
        ]
    )

    # 검증 실패 메시지를 프롬프트에 삽입
    retry_msg = ""
    if state.validation_error:
        retry_msg = "\n\n※ 지난 검증 결과:\n"
        for msg in state.validation_error:
            retry_msg += f"- {msg}\n"
        retry_msg += "→ 위 항목들의 조건을 꼭 반영해서 다시 작성해 주세요.\n"
    
    # 프롬프트 포맷팅
    formatted_prompt = messages.format(
        user_prompt=state.user_prompt + retry_msg,
        constraints=get_constraint_description(state.constraints),
        final_docs=state.embedded_data,
    )

    # LLM 호출
    response = llm.invoke(input=formatted_prompt).content
    print("🤖 전체 응답 결과:\n", response)

    # 항목별로 분할 (줄바꿈 기준)
    keys = list(state.constraints.keys())
    values = response.strip().split("\n")

    prompts = {}
    for i, key in enumerate(keys):
        value = values[i].strip() if i < len(values) else ""
        prompts[key] = value


    # 기존 state.result에 누적
    updated = state.result.copy()
    updated.update(prompts)
    print("🔄 병합된 result:", updated)

    return {
        "result": updated,
        "validation_error": None,  # 오류 상태 초기화
        "failed_keys": [],  # 실패 항목 초기화
    }
