import json
import time

from django.http import StreamingHttpResponse

from rest_framework import viewsets, status

from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import Prompt, PromptTest
from .serializers import PromptSerializer, PromptTestSerializer
from prompts.graphs.prompt_graph import create_ai_response_graph
from prompts.graphs.data_processing_graph import create_data_processing_graph


class PromptViewset(viewsets.ModelViewSet):
    queryset = Prompt.objects.all()
    serializer_class = PromptSerializer


class PromptTestViewset(viewsets.ModelViewSet):
    queryset = PromptTest.objects.all()
    serializer_class = PromptTestSerializer


def stream_prompt_result(prompt_app, prompt_state):
    # 1. LangGraph 실행 (동기)
    prompt_result = prompt_app.invoke(prompt_state)
    result_dict = prompt_result["result"]

    # 2. 제너레이터 정의
    def event_stream():
        for key, value in result_dict.items():
            chunk = json.dumps({key: value}, ensure_ascii=False)
            yield f"data: {chunk}\n\n"
            time.sleep(0.1)  # 선택적: UX 개선용 (클라이언트 처리 시간 고려)

        yield "data: [DONE]\n\n"

    # 3. 스트리밍 응답
    return StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )


class GeminiStreamingView(APIView):
    def post(self, request):
        try:
            body = request.data
            print("body: ", body)
            constraints = body.get("constraints", "")
            user_prompt = body.get("user_prompt", "").strip()
            product1 = body.get("product1", "")
            product2 = body.get("product2", "")

            if not user_prompt:
                return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)

            # 초기 상태 설정
            state = {
                "user_prompt": user_prompt,
                "product1": product1,
                "product2": product2,
                "reviews_data1": None,
                "reviews_data2": None,
                "products_data": None,
                "final_docs": None,
                "error": None,
            }

            # 1. 그래프 1 실행
            app = create_data_processing_graph()
            result = app.invoke(state)

            if result.get("error"):
                return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

            final_docs = result["final_docs"]  # 참조할 데이터

            # 2. 그래프 2 실행
            prompt_app = create_ai_response_graph()

            # 초기 상태
            prompt_state = {
                "constraints": constraints,
                "user_prompt": user_prompt,
                "embedded_data": final_docs,
                # "objective": "strength",
                # "constraints": {
                #    "R_1_1": {"max_length": 250, "format": "타사 비교했을 때 자사 제품의 강점 설명"},
                #    "R_1_2": {"max_length": 10, "format": "Apple 회사명 '~사'로 줄인 것 알려줘. 예를 들어, 회사명이 Hyundai일 경우 'H사'만 응답해."}
                # },
            }

            prompt_result = prompt_app.invoke(prompt_state)

            print("result[context]: ", prompt_result["result"])  # AI 답변

        except Exception as e:
            import traceback, sys

            traceback.print_exc(file=sys.stderr)
            return Response({"error": f"Invalid input: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        #return Response(prompt_result["result"])
        return stream_prompt_result(prompt_app=prompt_app, prompt_state=prompt_state)
