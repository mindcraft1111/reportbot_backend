import json

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
    prompt_result = prompt_app.invoke(prompt_state)
    result_dict = prompt_result["result"]
    if isinstance(result_dict, dict):
        result_str = json.dumps(result_dict, ensure_ascii=False)
    else:
        result_str = str(result_dict)

    def event_stream():
        text_output = json.dumps({'text': result_str}, ensure_ascii=False)
        print("🎯 Sending final result:", text_output)
        yield f"data: {text_output}\n\n"

    # 스트리밍 응답
    return StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


class GeminiStreamingView(APIView):
    def post(self, request):
        try:
            body = request.data
            print("body: ", body)
            user_prompt = body.get("user_prompt", "").strip()
            product1 = body.get("product1", "")
            product2 = body.get("product2", "")
            constraints = body.get("chunk_constraint", "")
            chunk_type = body.get("chunk_type", "")

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

            # 1. 그래프1 실행
            app = create_data_processing_graph()
            result = app.invoke(state)

            if result.get("error"):
                return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

            final_docs = result["final_docs"]  # 참조할 데이터

            # 2. 그래프2 실행
            prompt_app = create_ai_response_graph()

            # 초기 상태
            prompt_state = {
                "constraints": constraints,
                "user_prompt": user_prompt,
                "embedded_data": final_docs,
            }

        except Exception as e:
            import traceback, sys

            traceback.print_exc(file=sys.stderr)
            return Response({"error": f"Invalid input: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        return stream_prompt_result(prompt_app=prompt_app, prompt_state=prompt_state)
 