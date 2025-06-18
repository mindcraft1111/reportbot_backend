from rest_framework.response import Response


def api_response(code=1, msg="요청이 성공적으로 처리되었습니다.", data=None, errors=None, status_code=200, **kwargs):
    response = {
        "code": code,
        "msg": msg,
    }

    if data is not None:
        response["data"] = data
    
    if errors is not None:
        response["errors"] = errors
    
    # 추가 필드 병합
    response.update(kwargs)

    return Response(response, status=status_code)
