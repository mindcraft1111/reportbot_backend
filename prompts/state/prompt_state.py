from typing import Dict, Optional
from pydantic import BaseModel


class ConstraintSpec(BaseModel):
    max_length: Optional[int] = None
    format: Optional[str] = None # 사용자 입력 조건 텍스트


class PromptState(BaseModel):
    # 🎯 프롬프트 목적 및 제약조건
    constraints: Dict[str, ConstraintSpec] # 구조화된 제약조건
    user_prompt: Optional[str]  # 자연어 프롬프트

    # 📝 AI 결과 및 검증 상태
    result: Dict[str, str] = {} # AI 답변
    validation_error: Optional[list] = None # 검증 에러 목록
    failed_keys: Optional[list] = None # 실패 항목 추적용

    embedded_data: Optional[str] # 임베딩 데이터
