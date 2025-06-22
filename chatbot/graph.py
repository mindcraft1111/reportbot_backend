import os

from dotenv import load_dotenv
from typing_extensions import TypedDict
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories.redis import RedisChatMessageHistory
#from langchain_redis import RedisChatMessageHistory

from langgraph.graph import StateGraph, END
from chatbot.data_loader.retriever import get_context
from chatbot.chains import contextualize_chain, classify_chain, answer_chain


load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
print(f"Connecting to Redis at: {REDIS_URL}")


##################################################################
# Function to get or create a RedisChatMessageHistory instance
##################################################################
def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(session_id, url=REDIS_URL)


# 1. 상태 정의
class ChatbotState(TypedDict, total=False):
    product1: str
    product2: str
    question: str
    context: str
    classification: str
    session_id: str
    answer: str


# 2. 질문 구체화
def contextualize_question(state):
    result = contextualize_chain.invoke({
        # "hisory": state["history"],
        "history": state.get("history", []),
        "question": state["question"]
    })
    # 재작성된 질문을 state에 반영 (이후 분류 및 검색에 사용)
    return {"question": result.content.strip()}


# 3. 분류 노드
def classify_question(state):
    result = classify_chain.invoke({"question": state["question"]})
    return {"classification": result.content.strip().lower()}


# 4. 컨텍스트 노드
def retrieve_context(state):
    context = get_context(state)
    return {"context": context}


# 5. 응답 생성 노드

##################################################################
# Create a runnable with message history
##################################################################

# classify_chain은 일반 invoke()로 호출
# answer_chain만 사용자와의 대화 흐름을 유지
chain_with_history = RunnableWithMessageHistory(
    answer_chain,
    get_redis_history,
    input_messages_key="question",
    history_messages_key="history"
)


def generate_answer(state):
    session_id = state.get("session_id", "default")
    answer = chain_with_history.invoke(
        {
            "question": state["question"],
            "context": state["context"]
        },
        config={"configurable": {"session_id": session_id}}
    )
    return {"answer": answer}


# LangGraph 정의
def create_graph():
    builder = StateGraph(ChatbotState)

    # 노드 등록
    builder.add_node("contextualize_question", contextualize_question)
    builder.add_node("classify_question", classify_question)
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("generate_answer", generate_answer)

    # 진입점 -> 재작성된 질문으로 시작
    builder.set_entry_point("contextualize_question")

    # 노드 연결
    builder.add_edge("contextualize_question", "classify_question")
    builder.add_edge("classify_question", "retrieve_context")
    builder.add_edge("retrieve_context", "generate_answer")
    builder.add_edge("generate_answer", END)

    return builder.compile()


graph = create_graph()

# example
#initial_state: ChatbotState = {
#    "question": "자사 제품의 긍정적인 피드백 알려줘",
#    "product1": "1",
#    "product2": "2",
#    "session_id": "foo",
#    "classification": "own"
#}
#config = {"configurable": {"session_id": "foo"}}
#result = graph.invoke(initial_state)
#print(result)
