import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reportbot.settings')  # 프로젝트 이름 수정

import django
django.setup()

from langchain.schema.runnable import Runnable
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories.redis import RedisChatMessageHistory
#from langchain_redis import RedisChatMessageHistory
from langgraph.graph import StateGraph, END
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from prompts.llm.gemini import llm
from chatbot.prompts import ANSWER_PROMPT, contextualize_q_system_prompt
from chatbot.data_loader.retriever import get_context
import os
from chatbot.chains import classify_chain
from typing_extensions import TypedDict
from dotenv import load_dotenv


REDIS_URL="redis://localhost:6379"
#load_dotenv()
#
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
print(f"Connecting to Redis at: {REDIS_URL}")

##################################################################
# Function to get or create a RedisChatMessageHistory instance
##################################################################
def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(session_id, url=REDIS_URL)


## 상태 정의
class ChatbotState(TypedDict, total=False):
    product1: str
    product2: str
    question: str
    context: str
    classification: str
    session_id: str
    answer: str



# 0. 질문 구체화
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)
contextualize_chain: Runnable = contextualize_q_prompt | llm

def contextualize_question(state):
    result = contextualize_chain.invoke({
        # "hisory": state["history"],
        "history": state.get("history", []),
        "question": state["question"]
    })
    # 재작성된 질문을 state에 반영 (이후 분류 및 검색에 사용)
    return {"question": result.content.strip()}


# 1. 분류 노드
def classify_question(state):
    result = classify_chain.invoke({"question": state["question"]})
    return {"classification": result.content.strip().lower()}


# 2. 컨텍스트 노드
def retrieve_context(state):
    context = get_context(state)
    print("context: ", context)
    return {"context": context}


# 3. 응답 생성 노드
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ]
)

answer_chain = answer_prompt | llm | StrOutputParser()

# 세션 기록 저장할 딕셔너리
store = {}

# 세션 ID 기반으로 세션 기록 가져오는 함수
def get_session_history(session_id):
    print(f"[대화 세션ID]: {session_id}")
    if session_id not in store:  # 세션 ID가 store에 없는 경우
        # 새로운 ChatMessageHistory 객체를 생성하여 store에 저장
        store[session_id] = ChatMessageHistory()
    return store[session_id]  # 해당 세션 ID에 대한 세션 기록 반환


# 대화 기록하는 RAG 체인 생성 - 로컬
#rag_with_history = RunnableWithMessageHistory(
#    answer_chain,
#    get_session_history,  # 세션 기록을 가져오는 함수
#    input_messages_key="question",  # 사용자의 질문이 템플릿 변수에 들어갈 key
#    history_messages_key="history",  # 기록 메시지의 키
#)


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
    #answer = chain_with_history.invoke(
        {
            "question": state["question"],
            "context": state["context"]
        },
        # 세션 ID 기준으로 대화를 기록합니다.
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


while True:
    user_input = input("질문: ")
    state = {
        "product1": "1",
        "product2": "2",
        "session_id": "foo",
        "question": user_input
    }
    final_state = graph.invoke(state)
    history = final_state.get("history", [])
    if history:
        print("history: ", final_state["history"])
    print(f"🤖 답변: {final_state['answer']}\n")



# example
initial_state: ChatbotState = {
    "question": "자사 제품의 긍정적인 피드백 알려줘",
    "product1": "1",
    "product2": "2",
    "session_id": "foo",
    "classification": "own"
}
config = {"configurable": {"session_id": "foo"}}
result = graph.invoke(initial_state)
print(result)
second_state: ChatbotState = {
    # "question": "거기서 키워드 3개를 뽑아줘",
    "question": "내 이전 질문이 뭐였지?",
    "product1": "1",
    "product2": "2",
    "session_id": "foo",
    "classification": "own"
}
print(graph.invoke(second_state, config=config))