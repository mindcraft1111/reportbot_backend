from .views import PromptViewset, PromptTestViewset


def register_prompt_routes(router):
    router.register(r"prompts", PromptViewset)
    router.register(r"prompts-tests", PromptTestViewset)