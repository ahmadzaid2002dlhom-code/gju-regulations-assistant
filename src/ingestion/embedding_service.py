from __future__ import annotations

from typing import Protocol, Sequence

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Settings


class EmbeddingProvider(Protocol):
    def embed_document(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_key)
        self._model = settings.openai_embedding_model
        self._dimensions = settings.embedding_dimensions

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=10), reraise=True)
    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self._model,
            input=list(texts),
            dimensions=self._dimensions,
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]

    def embed_document(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]
