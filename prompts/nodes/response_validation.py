from prompts.llm.gemini import llm
from prompts.state.prompt_state import PromptState


# LLM 평가 노드: 자연어 설명(format)을 기준으로 적절성 판단
def validate_prompt_node(state: PromptState):
    print("\n🔍 LLM 기반 평가 시작")

    user_prompt = state.user_prompt
    failed = []
    errors = []

    for key, constraint in state.constraints.items():
        expected = constraint.format
        actual = state.result.get(key, "")
        print("💥actual: ", actual)

        if expected:
            eval_prompt = f"""
            당신은 보고서 평가자입니다.
            목표: {user_prompt}
            요소: {key}
            설명된 조건: "{expected}"
            응답 내용: "{actual}"
            
            이 응답이 설명에 적절하면 "적절"만 출력, 그렇지 않으면 "부적절"만 출력하세요.
            """
            result = llm.invoke(["system", eval_prompt]).content.strip()
            print(f"🧪 [{key}] LLM 평가 결과: {result}")
            
            if "부적절" in result:
                print(f"💥부적절함: [{key}]")
                errors.append(f"{key}: LLM 평가 부적절")
                failed.append(key)

                print("errors: ", errors)
                print("failed: ", failed)
    
    return {
        "validation_error": "\n".join(errors) if errors else None,
        "failed_keys": failed
    }
