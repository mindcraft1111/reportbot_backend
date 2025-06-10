from .views import PromptViewset, PromptTestViewset, UsedPromptViewset


def register_prompt_routes(router):
    router.register(r"prompts", PromptViewset)
    router.register(r"prompts-tests", PromptTestViewset)
    router.register(r"used-prompts", UsedPromptViewset)
