from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import Runnable

from prompts.llm.gemini import llm
from chatbot.prompts import contextualize_q_system_prompt, CLASSIFY_PROMPT, ANSWER_PROMPT


############################################
# 질문 문맥 반영하여 재정의 chain
############################################
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)

contextualize_chain: Runnable = contextualize_q_prompt | llm


############################################
# 질문 분류 chain
############################################
classify_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", CLASSIFY_PROMPT),
        ("human", "{question}")
    ]
)

classify_chain = classify_prompt | llm # 프롬프트와 모델 연결하여 runnable 객체 생성


############################################
# AI 응답 chain
############################################
answer_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", ANSWER_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ]
)

answer_chain = answer_prompt | llm
