"""Calc 계산 설명 규칙의 읽기 전용 데이터 구조."""

from pydantic import BaseModel, ConfigDict, model_validator


class CalcRule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    code: str
    name: str
    kind: str
    description_steps: list[str]
    input_fields: list[str]
    database_criteria: str | list[str]
    formulas_or_logic: str
    output: str
    special_notes: list[str]
    source_code: list[str]


class CalcRuleDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    metadata: dict[str, object]
    api_contract: dict[str, object]
    rules: list[CalcRule]
    chatbot_usage: dict[str, object]

    @model_validator(mode="after")
    def validate_unique_rule_codes(self):
        codes = [rule.code for rule in self.rules]
        if len(codes) != len(set(codes)):
            raise ValueError("Calc 규칙 코드가 중복되었습니다.")
        return self
