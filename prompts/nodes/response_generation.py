from prompts.llm.gemini import llm
from prompts.state.prompt_state import PromptState
from langchain.prompts import ChatPromptTemplate


def generate_prompt_node(state: PromptState):
    prompts = {}
    system_prompt = """
    너는 두 제품의 리뷰 데이터를 비교하고 분석하는 데이터 분석 전문가야. 
    타사 제품 대비 자사 제품의 장단점을 파악하고 개선점을 찾기 위해 
    그에 맞는 리포트 내부 텍스트를 작성하는 서비스를 제공 해줘.
    product1은 자사 제품이고, product2는 경쟁사 제품이야.
    제한된 토큰 안에서 내용이 부정확하거나 답변이 끊기는 등 제품 관련 질문에 대한 답변이 모호해지면 안돼.

    답변은 한국어로 작성해주고, 모르는 내용은 모른다고 답해줘.
    단, 반드시 사용자가 입력한 제약조건에 맞춰 응답해줘.
    
    ❗ 아래 규칙을 반드시 따르세요:
    - 불필요한 설명하지 마세요. **텍스트 설명 없이**
    - 불필요한 줄바꿈 없이 반환하세요
    - json 형식이 아니라 답변만 응답하세요

    예시:
    응답: "내용" 
    """

    messages = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "요청: {user_prompt}\n\n제약조건: {constraints}\n\nContext:\n{final_docs}")
    ])

    # 처음 생성이거나, 실패한 항목만 재생성
    if (state.failed_keys):
        print("⭐실패항목 key: ", state.failed_keys)

    target_keys = state.failed_keys if state.failed_keys else state.constraints.keys()

    for key in target_keys:
        spec = state.constraints[key]
        constraint_desc = []
        if spec.max_length:
            constraint_desc.append(f"{spec.max_length}자 이하")
        if spec.format:
            constraint_desc.append(f"{spec.format}")
    
        constraints = f'"{key}": {", ".join(constraint_desc)}'
        print("constraints: ", constraints)

        formatted_prompt = messages.format(user_prompt=state.user_prompt, constraints=constraints, final_docs=state.embedded_data)
        print(f"✉️ LLM에게 요청할 메시지:\n{formatted_prompt}")
        
        # 요청 (stream)
        response = llm.invoke(input=formatted_prompt).content
        print(f"🤖 응답({key}):", response)

        prompts[key] = response
    
    # 기존 것 유지 + 새로 생성된 것 병합
    updated = state.result.copy()
    updated.update(prompts)
    print("🔄 병합된 result:", updated)
    return {
        "result": updated,
        "validation_error": None, # 오류 상태 초기화
        "failed_keys": [] # 실패 항목 초기화
    }
