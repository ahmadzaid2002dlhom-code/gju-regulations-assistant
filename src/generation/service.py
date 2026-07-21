from __future__ import annotations

from src.generation.answer_generator import GenerationProvider
from src.models import AssistantAnswer
from src.retrieval.context_builder import build_evidence
from src.retrieval.service import HybridRetriever


class QuestionAnsweringService:
    def __init__(
        self,
        retriever: HybridRetriever,
        generator: GenerationProvider,
    ) -> None:
        self._retriever = retriever
        self._generator = generator

    def answer(
        self,
        question: str,
        *,
        document_type: str | None = None,
        language: str | None = "auto",
        safety_identifier: str | None = None,
    ) -> AssistantAnswer:
        hits, _classification = self._retriever.retrieve(
            question,
            document_type=document_type,
            language=language,
        )
        evidence = build_evidence(hits, len(hits))
        if not evidence:
            return AssistantAnswer(
                text="I could not find relevant evidence in the currently indexed official documents.",
                sources=[],
            )
        text = self._generator.answer(
            question,
            evidence,
            safety_identifier=safety_identifier,
        )
        return AssistantAnswer(text=text, sources=evidence)
