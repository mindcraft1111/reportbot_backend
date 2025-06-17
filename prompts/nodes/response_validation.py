from prompts.llm.gemini import llm
from prompts.state.prompt_state import PromptState


def validate_prompt_node(state: PromptState):
    print("\n🔍 LLM 기반 평가 시작")

    user_prompt = state.user_prompt
    constraints = state.constraints
    result = state.result

    failed_keys = []
    error_msgs = []

    # 1. max_length 검증 (key 단위)
    for key, constraint in constraints.items():
        actual = result.get(key, "")
        if constraint.max_length and len(actual) > constraint.max_length:
            print(f"💥{key}: {len(actual)}자 (최대 {constraint.max_length}자 초과)")
            
            error_msgs.append(f"{key}: {constraint.max_length}자 이내로 줄여야 합니다 (현재 {len(actual)}자)")
            failed_keys.append(key)

    # 2. format 기반 LLM 평가 (전체 기준)
    # 전체 제약조건 설명 문자열 만들기
    format_desc = "\n".join([
        f"{key}: {constraint.format}" for key, constraint in constraints.items() if constraint.format
    ])

    # 전체 응답 결과 문자열 만들기
    result_desc = "\n".join([
        f"{key}: {result.get(key, '')}" for key in constraints
    ])

    eval_prompt = f"""
    당신은 보고서 평가자입니다.
    
    사용자의 요청:
    {user_prompt}

    요구된 응답 형식 설명:
    {format_desc}

    AI가 생성한 응답 결과:
    {result_desc}

    각 항목에 대해 응답이 설명에 적절하지 않다면 다음과 같은 형식으로 알려주세요:
    - r_1_1: 형식 불일치 (예: xxx)
    - r_1_3: 형식 아님

    모두 적절하다면 "적절"이라고만 응답하세요.
    """

    llm_result = llm.invoke(["system", eval_prompt]).content.strip()
    print("🧪 LLM 평가 전체 결과:\n", llm_result)

    if "적절" not in llm_result.lower():
        lines = llm_result.strip().splitlines()
        for line in lines:
            if ":" in line:
                key = line.split(":")[0].strip()
                failed_keys.append(key)
                error_msgs.append(line.strip())

    return {
        "validation_error": error_msgs if error_msgs else None,
        "failed_keys": failed_keys
    }
