"""검색·모델 호출 전 질문 정책. 이력은 주제·의도에만 쓰고 계산 근거로 쓰지 않는다."""

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.chat import ChatRequest
from app.services.calc_rules import RULE_ALIASES

OUT_OF_SCOPE_MESSAGE = (
    "저는 연말정산과 절세 관련 정보를 안내하는 희망환급 AI 챗봇입니다. "
    "연말정산 예상 결과, 소득공제·세액공제, 청년 세제 혜택 등 서비스와 관련된 질문을 해주세요."
)
SIMULATION_MESSAGE = (
    "입력 조건을 바꾼 새로운 세액·환급액·공제액은 이 대화에서 직접 계산하거나 추정하지 않습니다. "
    "희망환급의 조건 변경 시뮬레이션에서 변경할 입력값으로 계산 결과를 확인해 주세요."
)
OTHER_TAX_MESSAGE = (
    "질문하신 세목은 연말정산 중심의 희망환급 안내 범위 밖입니다. "
    "해당 세목의 공식 안내나 전문 상담을 통해 확인해 주세요."
)
CLARIFY_MESSAGE = (
    "어떤 항목에 대해 알고 싶으신가요? 현재 적용액, 계산 원리, "
    "조건을 바꾼 시뮬레이션 중 원하는 내용을 알려주세요."
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


_TAX_TOPICS = (
    "연말정산",
    "소득공제",
    "세액공제",
    "공제",
    "감면",
    "환급",
    "추가납부",
    "결정세액",
    "기납부세액",
    "과세표준",
    "산출세액",
    "절세",
    "총급여",
    "청년세제",
    "의료비",
    "교육비",
    "기부금",
    "부양가족",
    "보험료",
    "원천징수",
)
_SERVICE = ("희망환급", "시뮬레이션", "챗봇", "로그인", "회원가입", "탈퇴")
_OTHER_TAX = (
    "상속세",
    "증여세",
    "양도소득세",
    "법인세",
    "부가가치세",
    "부가세",
    "취득세",
    "종합부동산세",
    "관세",
    "양도세",
    "재산세",
    "종부세",
    "종합소득세",
    "증권거래세",
)
_UNRELATED = (
    "날씨",
    "점심",
    "맛집",
    "파스타",
    "파이썬",
    "코딩",
    "축구",
    "운세",
    "영화추천",
    "여행추천",
    "주식추천",
)
_METHOD = ("원리", "방식", "산식", "계산법", "계산방법", "어떻게계산", "계산과정")
_CHANGE = re.compile(
    r"시뮬레이션|재계산|다시계산|"
    r"(?:바꾸|변경|늘리|늘렸|올리|올랐|오르|줄이|줄였|낮추|낮췄|추가하|더넣|더내|더납입|추가납입|빼|없애|이직|퇴사|결혼).{0,30}(?:면|경우|가정|후|때|계산|시)|"
    r"(?:만원|원|명|개월|%).{0,3}(?:으로|로|이면|이라면|일때).{0,15}(?:하면|바꾸|변경|계산|환급|공제|세액|얼마|절세)|"
    r"(?:가정|조건변경).{0,35}(?:얼마|세액|환급|공제|계산)|"
    r"(?:납입|넣|내|사용|지출|벌|받).{0,4}(?:으면|는다면|하면|한다면).{0,20}(?:얼마|환급|절세|공제|세액)|"
    r"(?:원|명|개월)더(?:[?!.]|$)"
)


@dataclass(frozen=True)
class QuestionDecision:
    kind: Literal[
        "CONTINUE", "SIMULATION", "MIXED", "OUTSIDE", "OTHER_TAX", "CLARIFY", "SERVICE"
    ]
    question: str
    topic: str | None = None


def _topics(text: str) -> set[str]:
    return {
        code
        for code, aliases in RULE_ALIASES.items()
        if any(normalize(alias) in text for alias in aliases)
    }


def _related(text: str) -> bool:
    return bool(_topics(text)) or any(
        term in text for term in (*_TAX_TOPICS, *_SERVICE)
    )


def _change_intent(text: str) -> bool:
    # 재계산을 명시적으로 제외한 원리 질문을 조건 변경으로 오인하지 않는다.
    probe = re.sub(
        r"(?:시뮬레이션|재계산|다시계산)(?:은|는|을)?(?:말고|제외하고|하지말고|하지마|하지않고|아니라)",
        "",
        text,
    )
    if re.search(r"입력된|계산된|저장된|적용된", probe) and not re.search(
        r"시뮬레이션|재계산|다시계산|바꾸|변경|늘리|올리|줄이|추가|더넣|더내|더납입",
        probe,
    ):
        return False
    return bool(_CHANGE.search(probe))


def _short_or_contextual(text: str) -> bool:
    if text.rstrip("?!.") in {
        "그건",
        "그거",
        "이건",
        "이거",
        "그공제",
        "그항목",
        "그럼",
        "그러면",
        "알려주세요",
        "설명해주세요",
        "도와줘",
        "도와주세요",
        "추천해줘",
        "추천해주세요",
    }:
        return True
    aliases = {normalize(alias) for values in RULE_ALIASES.values() for alias in values}
    return text.rstrip("?!.") in aliases or bool(
        re.fullmatch(
            r"(?:그럼|그러면|그래서|그건|그거|그공제|그항목|이건|이거)?"
            r"(?:은|는|도|요|어떻게|계산|원리|방식|얼마|인가요|예요|야|죠|해줘|설명|알려줘|나요|되나요|하면|더넣으면|넣으면|\d|만원|원|더|조금|[?!. ])+",
            text,
        )
    )


def classify_question(request: ChatRequest) -> QuestionDecision:
    question = request.message
    text = normalize(question)
    recent = [item.content for item in request.history if item.role == "user"][-2:]
    # 명확한 현재 주제 전환은 이전 대화보다 우선한다.
    other_tax = any(term in text for term in _OTHER_TAX)
    if other_tax:
        kind = (
            "CLARIFY"
            if any(term in text for term in ("연말정산", "희망환급"))
            else "OTHER_TAX"
        )
        return QuestionDecision(kind, question)
    related = _related(text) or bool(
        request.tax_result
        and any(
            normalize(value) in text
            for detail in request.tax_result.details
            for value in (detail.type_name, detail.type_code)
        )
    )
    if any(term in text for term in _UNRELATED):
        mixed_request = bool(_topics(text)) and any(
            term in text for term in (*_METHOD, "얼마", "알려")
        )
        return QuestionDecision("CLARIFY" if mixed_request else "OUTSIDE", question)

    contextual = _short_or_contextual(text)
    context = normalize(recent[-1]) if recent else ""
    # 직전 사용자 발화가 짧은 항목명이면 한 단계 전의 의도까지 확인한다.
    intent_context = context
    if context and _short_or_contextual(context) and len(recent) == 2:
        intent_context = normalize(recent[-2])
    topics = _topics(text) or (_topics(context) if contextual else set())
    topic = next(iter(topics)) if len(topics) == 1 else None
    if contextual and not related and context and not _related(context):
        return QuestionDecision(
            "OTHER_TAX" if any(term in context for term in _OTHER_TAX) else "CLARIFY",
            question,
        )
    changed = _change_intent(text)
    inherited_change = (
        contextual and _related(context) and _change_intent(intent_context)
    )
    if (related or (contextual and _related(context))) and (
        changed or inherited_change
    ):
        return QuestionDecision(
            "MIXED" if any(term in text for term in _METHOD) else "SIMULATION",
            question,
            topic,
        )
    if contextual:
        if (
            not related
            and topic is not None
            and "얼마" in text
            and "얼마" in context
            and not _change_intent(context)
        ):
            alias = next(
                (alias for alias in RULE_ALIASES[topic] if normalize(alias) in context),
                None,
            )
            if alias:
                resolved = f"{alias} {'입력액' if '입력' in context else '공제 적용액'}은 얼마인가요?"
                return QuestionDecision("CONTINUE", resolved, topic)
        return QuestionDecision("CLARIFY", question, topic)
    if related and "절세" in text and any(term in text for term in ("얼마", "금액")):
        return QuestionDecision("CLARIFY", question, topic)
    if related:
        if (
            any(term in text for term in _SERVICE)
            and not any(term in text.replace("희망환급", "") for term in _TAX_TOPICS)
            and not _topics(text)
        ):
            return QuestionDecision("SERVICE", question)
        return QuestionDecision("CONTINUE", question, topic)
    if any(term in text for term in ("세금", "세법", "세율")):
        return QuestionDecision("CLARIFY", question)
    return QuestionDecision("OUTSIDE", question)
