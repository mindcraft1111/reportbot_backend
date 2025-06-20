from typing import Dict, List, Type

from pydantic import BaseModel, Field

# 01 COVER PAGE


class C001(BaseModel):
    r_0_1: str = Field(description="report_title", max_length=25)


class C002(BaseModel):
    r_0_2: str = Field(description="report_objective", max_length=20)


# 02

## 없음

# 03 SWOT PAGE


class C031(BaseModel):
    r_3_1: str = Field(description="strength_title", max_length=15)
    r_3_2: str = Field(description="strength_description", max_length=56)


class C032(BaseModel):
    r_3_3: str = Field(description="weakness_title", max_length=15)
    r_3_4: str = Field(description="weakness_description", max_length=47)


class C033(BaseModel):
    r_3_5: str = Field(description="opportunity_title", max_length=15)
    r_3_6: str = Field(description="opportunity_description", max_length=63)


class C034(BaseModel):
    r_3_7: str = Field(description="threat_title", max_length=15)
    r_3_8: str = Field(description="threat_description", max_length=56)


# 04 selfProductPage


class C041(BaseModel):
    r_4_1_1: int = Field(description="positive_ratio")
    r_4_1_2: int = Field(description="negative_ratio")


class C042(BaseModel):
    r_4_3: str = Field(description="positive_icon_1", max_length=3)
    r_4_4: str = Field(description="positive_title_1", max_length=10)
    r_4_5: str = Field(description="positive_summary_1", max_length=20)
    r_4_6: str = Field(description="positive_icon_2", max_length=3)
    r_4_7: str = Field(description="positive_title_2", max_length=10)
    r_4_8: str = Field(description="positive_summary_2", max_length=20)
    r_4_9: str = Field(description="positive_icon_3", max_length=3)
    r_4_10: str = Field(description="positive_title_3", max_length=10)
    r_4_11: str = Field(description="positive_summary_3", max_length=20)


class C043(BaseModel):
    r_4_12: str = Field(description="negative_icon_1", max_length=3)
    r_4_13: str = Field(description="negative_title_1", max_length=10)
    r_4_14: str = Field(description="negative_summary_1", max_length=20)
    r_4_15: str = Field(description="negative_icon_2", max_length=3)
    r_4_16: str = Field(description="negative_title_2", max_length=10)
    r_4_17: str = Field(description="negative_summary_2", max_length=20)
    r_4_18: str = Field(description="negative_icon_3", max_length=3)
    r_4_19: str = Field(description="negative_title_3", max_length=10)
    r_4_20: str = Field(description="negative_summary_3", max_length=20)


class C044(BaseModel):
    r_4_21: str = Field(description="overall_summary", max_length=193)


# 05 competitorPage


class C051(BaseModel):
    r_5_2_1: List[int] = Field(
        description="sentiment_positive_scores [자사, 타사]", max_items=2
    )
    r_5_2_2: List[int] = Field(
        description="sentiment_negative_scores [자사, 타사]", max_items=2
    )


class C052(BaseModel):
    r_5_3: str = Field(description="competitor_name", max_length=20)
    r_5_4: str = Field(description="competitor_strength_1", max_length=16)
    r_5_5: str = Field(description="competitor_strength_2", max_length=16)
    r_5_6: str = Field(description="competitor_strength_3", max_length=16)



class C053(BaseModel):
    r_5_7: str = Field(description="competitor_summary", max_length=166)


# ✅ Full parser registry
PARSER_REGISTRY: Dict[str, Type[BaseModel]] = {
    "C001": C001,
    "C002": C002,
    "C031": C031,
    "C032": C032,
    "C033": C033,
    "C034": C034,
    "C041": C041,
    "C042": C042,
    "C043": C043,
    "C044": C044,
    "C051": C051,
    "C052": C052,
    "C053": C053,
}
