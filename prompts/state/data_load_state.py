from typing import Optional
from pydantic import BaseModel


# =============================================
# 상태 정의
# =============================================
class StateDict(BaseModel):
    user_prompt: str
    product1: str
    product2: str
    reviews_data1: Optional[str]
    reviews_data2: Optional[str]
    products_data: Optional[str]
    final_docs: Optional[str]
    error: Optional[str]
