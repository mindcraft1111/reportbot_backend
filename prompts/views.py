import uuid
from django.utils import timezone
from django.http import JsonResponse

from .models import ReportTemplate, Prompt, PromptTest, UsedPrompt

from rest_framework import status
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from langchain_google_genai import ChatGoogleGenerativeAI
from .serializers import PromptSerializer, PromptTestSerializer, UsedPromptSerializer
from dotenv import load_dotenv
from .llm.gemini_ import analyze_review_with_gemini


load_dotenv()

# 채팅에 사용할 모델
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)


class PromptViewset(viewsets.ModelViewSet):
    queryset = Prompt.objects.all()
    serializer_class = PromptSerializer


class PromptTestViewset(viewsets.ModelViewSet):
    queryset = PromptTest.objects.all()
    serializer_class = PromptTestSerializer


class UsedPromptViewset(viewsets.ModelViewSet):
    queryset = UsedPrompt.objects.all()
    serializer_class = UsedPromptSerializer


"""
class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
"""

"""
class PromptResponseViewSet(viewsets.ModelViewSet):
    queryset = PromptResponse.objects.all()
    serializer_class = PromptResponseSerializer
"""


class PromptAnalyzeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        input_prompt = request.data.get("input_prompt")
        if not input_prompt:
            return Response(
                {"error": "input_prompt is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = analyze_review_with_gemini(model, input_prompt)
            return Response({"result": result})
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


##################################################################
# 테스트용
##################################################################
def create_sample_report_template(request):
    if request.method == "GET":
        template_data = {
            "sections": [
                {
                    "id": "title",
                    "label": "리포트 제목",
                    "type": "text",
                    "constraints": {"max_length": 30, "must_end_with": "명사"},
                    "description": "헤드라인 형식으로 작성. 주제를 잘 드러낼 것",
                },
                {
                    "id": "summary",
                    "label": "요약",
                    "type": "text",
                    "constraints": {
                        "max_length": 200,
                        "tone": "중립",
                        "style": "bullet",
                    },
                    "description": "자사와 경쟁사 제품 리뷰를 한눈에 비교할 수 있도록 핵심만 요약",
                },
            ]
        }

        obj = ReportTemplate.objects.create(
            id=uuid.uuid4(),
            name="헤드폰 리뷰 분석 템플릿 (GET 테스트용)",
            structure_json=template_data,
        )

        return JsonResponse(
            {
                "message": "템플릿이 성공적으로 생성되었습니다.",
                "template_id": str(obj.id),
                "template_name": obj.name,
            }
        )
    else:
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)


def create_structured_prompts(request):
    if request.method == "GET":
        try:
            template = ReportTemplate.objects.latest("updated_at")
        except ReportTemplate.DoesNotExist:
            return JsonResponse(
                {"error": "ReportTemplate이 존재하지 않습니다."}, status=400
            )

        structure = template.structure_json.get("sections", [])
        prompts = []

        for section in structure[:10]:  # 최대 10개만 생성
            section_id = section.get("id")
            label = section.get("label", "")
            description = section.get("description", "")
            constraints = section.get("constraints", {})

            # constraint 설명 생성
            constraint_summary = []
            if "max_length" in constraints:
                constraint_summary.append(f"{constraints['max_length']}자 이내")
            if "must_end_with" in constraints:
                constraint_summary.append(f"{constraints['must_end_with']}로 끝나야 함")
            if "tone" in constraints:
                constraint_summary.append(f"{constraints['tone']} 어조")
            if "style" in constraints:
                constraint_summary.append(f"{constraints['style']} 형식")
            if "sentence_limit" in constraints:
                constraint_summary.append(f"최대 {constraints['sentence_limit']}문장")

            constraint_text = ", ".join(constraint_summary)

            prompt_text = f"""
                {label} 항목에 대한 내용을 생성해줘.
                설명: {description}
                작성 조건: {constraint_text if constraint_text else '제한 없음'}
                """.strip()

            prompts.append(
                Prompt(
                    id=uuid.uuid4(),
                    template=template,
                    section_id=section_id,
                    name=label,
                    prompt_text=prompt_text,
                    created_at=timezone.now(),
                )
            )

        Prompt.objects.bulk_create(prompts)

        return JsonResponse(
            {
                "message": f"{len(prompts)}개의 프롬프트가 생성되었습니다.",
                "template_id": str(template.id),
                "prompt_ids": [str(p.id) for p in prompts],
            }
        )

    return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)


# 프롬프트 응답 받아오기 테스트
def analyze_all_prompts(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET 요청만 허용됩니다."}, status=405)

    prompts = Prompt.objects.all()[:10]  # 예시로 상위 10개만 처리
    results = []

    for prompt in prompts:
        try:
            result = analyze_review_with_gemini(model, prompt.prompt_text)
            results.append(
                {
                    "prompt_id": str(prompt.id),
                    "section_id": prompt.section_id,
                    "prompt_text": prompt.prompt_text,
                    "response": result,
                }
            )
        except Exception as e:
            results.append({"prompt_id": str(prompt.id), "error": str(e)})

    return JsonResponse({"results": results})
