from dotenv import load_dotenv
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


class GeminiLLM(Runnable):
    def __init__(self, model_name="gemini-2.0-flash", temperature=0):
        self.model = ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

    def invoke(self, *args, **kwargs):
        return self.model.invoke(*args, **kwargs)

    def as_langchain_chat_model(self):
        return self.model


llm = GeminiLLM().as_langchain_chat_model()
