from langchain_chroma import Chroma
from prompts.llm.embedding import embeddings

# 임베딩 모델 로드


class VectorDBWrapper:
    def __init__(self, product_id: str, embedding_model=embeddings, base_path="./vectordb/reviews"):
        self.product_id = product_id
        self.db = Chroma(
            persist_directory=f"{base_path}/product_{product_id}",
            collection_name=f"reviews_product_{product_id}",
            embedding_function=embedding_model
        )

    def search(self, query: str, k: int = 30):
        return self.db.as_retriever(search_kwargs={"k": k}).invoke(query)
