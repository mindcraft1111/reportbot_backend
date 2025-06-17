################################################################################################
# prompt test
################################################################################################
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from google import genai
from django.views.decorators.csrf import csrf_exempt
import json

from .workflow import create_analysis_workflow


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
{chunk_constraint}

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

다음 질문에 대해 반드시  데이터에서만 확인된 수치로만 답하세요. 임의로 숫자를 추정하거나 생성하지 마세요.
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
