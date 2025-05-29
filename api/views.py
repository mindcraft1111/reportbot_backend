from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


# Create your views here.
def index(request):

    data = {"msg": "서버가 작동 중입니다."}

    print("update")

    return JsonResponse(
        data, safe=False, json_dumps_params={"ensure_ascii": False}, status=200
    )
