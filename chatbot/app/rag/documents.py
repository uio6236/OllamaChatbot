"""추출 모델에서 기존 Source 및 LangChain Document로 명시적으로 변환한다."""

from langchain_core.documents import Document

from app.rag.models import Chunk
from app.schemas.common import Source


def to_source(chunk: Chunk) -> Source:
    data = chunk.model_dump(by_alias=True)
    keys = {field.alias for field in Source.model_fields.values()}
    return Source.model_validate(
        {key: value for key, value in data.items() if key in keys}
    )


def to_document(chunk: Chunk) -> Document:
    metadata = chunk.model_dump(by_alias=True, exclude={"content", "source_spans"})
    return Document(id=chunk.chunk_id, page_content=chunk.content, metadata=metadata)
