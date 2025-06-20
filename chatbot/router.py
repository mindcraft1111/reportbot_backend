from .views import ChatbotViewset


def register_chatbot_routes(router):
    router.register(r"chat", ChatbotViewset)