import json, os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import RedisChatMessageHistory

from api.models.users import Users
from api.models.chatbot import ChatSession, ChatMessage, LangGraphLog

from chatbot.graph import create_graph


def save_message_to_db(user: Users, session_id: str, sender: str, content: str):
    session, _ = ChatSession.objects.get_or_create(user=user, session_id=session_id)
    ChatMessage.objects.create(session=session, sender=sender, content=content)


def save_langgraph_node_log(session_id: str, node_name: str, input_data: str, output_data: str):
    session = ChatSession.objects.get(session_id=session_id)
    LangGraphLog.objects.create(
        session=session,
        node_name=node_name,
        input_summary=input_data,
        output_summary=output_data,
    )


# 임시: 비로그인 사용자용 세션 ID 할당
def get_or_create_session(user):
    session_id = f"{user.username}_session"
    session, _ = ChatSession.objects.get_or_create(user=user, session_id=session_id)
    return session, session_id


@csrf_exempt
def chat_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        user_input = data.get("message", "")
        product1 = data.get("product1", "")
        product2 = data.get("product2", "")

        # 가정: request.user 사용 (로그인된 사용자 기준)
        user = request.user if request.user.is_authenticated else Users.objects.first()  # 테스트용 fallback

        # 1. 세션/히스토리 준비
        session, session_id = get_or_create_session(user)
        redis_url = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}"
        history = RedisChatMessageHistory(session_id=session_id, url=redis_url)
        
        # 2. 유저 메시지 저장 (Redis + DB)
        history.add_message(HumanMessage(content=user_input))
        ChatMessage.objects.create(session=session, sender="user", content=user_input)

        # 3. LangGraph 실행
        graph = create_graph()
        result = graph.invoke({
            "session_id": session_id,
            "question": user_input,
            "product1": product1,
            "product2": product2
        })
        
        ai_response = result.get("answer", "답변이 없습니다.")

        # 4. AI 응답 저장 (Redis + DB)
        history.add_message(AIMessage(content=ai_response.content))
        ChatMessage.objects.create(session=session, sender="ai", content=ai_response)
        messages = history.messages
        for m in messages:
            print(f"{m.type}: {m.content}")
        
        return JsonResponse({
            "status": "success",
            "response": ai_response.content,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
