from typing import Dict, Optional
from pydantic import BaseModel, model_validator


class ConstraintSpec(BaseModel):
    max_length: Optional[int] = None
    format: Optional[str] = None # 사용자 입력 조건 텍스트


class PromptState(BaseModel):
    # 🎯 프롬프트 목적 및 제약조건
    constraints: Dict[str, ConstraintSpec] # 구조화된 제약조건
    user_prompt: Optional[str]  # 자연어 프롬프트

    # 📝 AI 결과 및 검증 상태
    result: Dict[str, str] = {} # AI 답변
    validation_error: Optional[str] = None # 검증 에러 목록
    failed_keys: Optional[list] = None # 실패 항목 추적용

    embedded_data: Optional[str] # 임베딩 데이터

    @model_validator(mode="after")
    def check_constraints(self) -> "PromptState":
        """max_length 기준 검증"""
        errors = []
        failed_keys = []

        for key, constraint in self.constraints.items():
            value = self.result.get(key)
            if value is None: # format 검증은 따로 하므로 여기서는 skip
                continue

            if constraint.max_length and len(value) > constraint.max_length:
                errors.append(f"{key}: 최대 {constraint.max_length}자를 초과했습니다. ({value}: {len(value)}자 입력됨)")
                print(f"💥{key}: 최대 {constraint.max_length}자를 초과했습니다. ({value}: {len(value)}자 입력됨)")
                failed_keys.append(key)

        self.validation_error = "\n".join(errors) if errors else None
        self.failed_keys = failed_keys
        if errors:
            print("📱model validate 에러 추가: ", self.failed_keys)

        return self
