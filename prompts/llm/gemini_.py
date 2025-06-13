from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate


def analyze_review_with_gemini(model, input_prompt):
    system_prompt = SystemMessagePromptTemplate.from_template(
        "너는 리뷰를 비교 분석해서 리포트를 작성하는 전문가야."
    )

    user_prompt = """
    리포트 작성을 위해 다음 조건에 맞는 응답을 생성해줘. 응답 외에 텍스트 해설은 하지 마.

    {input_prompt}
    """

    prompt_template = ChatPromptTemplate.from_messages([system_prompt, user_prompt])
    # 변수를 바인딩해서 메시지 생성
    prompt = prompt_template.format(input_prompt=input_prompt)

    result = model.invoke(prompt)
    print("result: ", result)
    return result.content
