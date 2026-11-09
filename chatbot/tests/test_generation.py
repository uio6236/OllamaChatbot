"""짧은 Mock 작업으로 응답 대기 제한을 검증한다. 실제 추론 취소 검증은 아니다."""

import asyncio
import threading
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core.config import InternalApiSettings
from app.core.errors import InternalApiError
from app.schemas.common import Source
from app.schemas.recommendation import Recommendation
from app.services.generation import GenerationService, UnavailableRetriever


def test_model_wait_timeout_does_not_release_running_slot():
    started = threading.Event()
    release = threading.Event()
    model = Mock()

    def slow_generate(prompt):
        started.set()
        release.wait(timeout=2)
        return "테스트 답변"

    model.generate.side_effect = slow_generate
    service = GenerationService(
        UnavailableRetriever(), model, InternalApiSettings(model_timeout=0.05)
    )

    async def scenario():
        try:
            with pytest.raises(InternalApiError) as timeout_error:
                await service.generate({}, [])
            assert timeout_error.value.code == "OLLAMA_TIMEOUT"
            assert started.is_set()
            with pytest.raises(InternalApiError) as busy_error:
                await service.generate({}, [])
            assert busy_error.value.code == "MODEL_BUSY"
        finally:
            release.set()

    asyncio.run(scenario())


def test_recommendation_forbids_saving_amount():
    with pytest.raises(ValidationError):
        Recommendation(
            typeCode=None, content="테스트", model="test", sources=[], savingAmount=10
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"effectiveDate": "2026-02-30"},
        {"pageEnd": 0},
        {"pageStart": 3, "pageEnd": 2},
        {"sourceFile": "C:\\private\\test.pdf"},
        {"applicabilityVerified": True, "applicableTaxYear": None},
    ],
)
def test_source_validation(updates):
    data = {
        "chunkId": "test",
        "documentVersion": "test",
        "documentTitle": "테스트",
        "article": None,
        "sourceFile": "test.pdf",
        "sourceUrl": None,
        "pageStart": 1,
        "pageEnd": 1,
        "effectiveDate": None,
        "applicableTaxYear": 2026,
        "applicabilityVerified": True,
    }
    with pytest.raises(ValidationError):
        Source.model_validate({**data, **updates})
