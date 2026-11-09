"""기본 검색기는 미준비다. 테스트에서만 의존성을 대체한다."""

from app.services.generation import GenerationService, UnavailableRetriever


def get_generation() -> GenerationService:
    return GenerationService(UnavailableRetriever())
