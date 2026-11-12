"""로컬 Calc 규칙 파일을 검증하고 항목 코드로 조회한다."""

import json
import re
from functools import lru_cache
from pathlib import Path

from app.schemas.calc_rule import CalcRule, CalcRuleDocument
from app.schemas.common import DeductionDetail

RULES_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "rules"
    / "희망환급_Calc_계산설명규칙.json"
)


class CalcRuleCatalog:
    def __init__(self, rules: list[CalcRule]):
        self._by_code = {rule.code: rule for rule in rules}

    @classmethod
    def load(cls, path: Path = RULES_PATH) -> "CalcRuleCatalog":
        document = CalcRuleDocument.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )
        return cls(document.rules)

    def get_for_detail(self, detail: DeductionDetail) -> CalcRule | None:
        code = detail.type_code
        if detail.kind in {"CARD", "CARD_RULE"}:
            code = "CARD"
        return self._by_code.get(code)

    def get(self, code: str) -> CalcRule | None:
        return self._by_code.get(code)

    def find_for_question(self, question: str) -> CalcRule | None:
        normalized_question = _normalize(question)
        matches = []
        for rule in self._by_code.values():
            terms = (rule.code, rule.name, *RULE_ALIASES.get(rule.code, ()))
            if any(
                normalized_term and normalized_term in normalized_question
                for normalized_term in map(_normalize, terms)
            ):
                matches.append(rule)
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def might_match_question(question: str) -> bool:
        normalized_question = _normalize(question)
        return any(
            _normalize(alias) in normalized_question
            for aliases in RULE_ALIASES.values()
            for alias in aliases
        )


@lru_cache(maxsize=1)
def get_calc_rule_catalog() -> CalcRuleCatalog:
    return CalcRuleCatalog.load()


def _normalize(value: str) -> str:
    return re.sub(r"[^0-9A-Z가-힣]", "", value.upper())


RULE_ALIASES = {
    "EARNED_DEDUCTION": ("근로소득공제",),
    "PERSON_BASIC": ("기본공제", "인적공제"),
    "NATIONAL_PENSION": ("국민연금",),
    "HEALTH_INSURANCE": ("건강보험", "고용보험"),
    "HOUSING_SAVING": ("주택청약", "청약저축"),
    "CARD": ("신용카드", "체크카드", "카드공제", "카드 사용"),
    "SME_YOUTH": ("중소기업취업자", "중소기업", "청년감면"),
    "EARNED_CREDIT": ("근로소득세액공제", "근로세액공제"),
    "PENSION": ("연금저축", "연금계좌", "IRP"),
    "RENT": ("월세",),
    "STANDARD_CREDIT": ("표준세액공제", "표준공제"),
    "TAXABLE_INCOME": ("과세표준",),
    "TAX_RATE": ("산출세액",),
    "DECIDED_TAX": ("결정세액",),
    "EXPECTED_REFUND": ("환급액", "추가납부액", "추가 납부액"),
    "BENEFIT_DIAGNOSIS": ("혜택 자격 진단",),
}
