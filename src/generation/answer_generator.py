from __future__ import annotations

from typing import Protocol

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Settings
from src.generation.citation_builder import ensure_source_references
from src.generation.prompts import SYSTEM_PROMPT, build_user_prompt
from src.models import EvidenceSource
from src.retrieval.context_builder import format_evidence


class GenerationProvider(Protocol):
    def answer(
        self,
        question: str,
        evidence: list[EvidenceSource],
        *,
        safety_identifier: str | None = None,
    ) -> str: ...


class OpenAIGenerationProvider:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_key)
        self._model = settings.openai_generation_model
        self._max_output_tokens = settings.max_answer_tokens

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def answer(
        self,
        question: str,
        evidence: list[EvidenceSource],
        *,
        safety_identifier: str | None = None,
    ) -> str:
        request: dict[str, object] = {
            "model": self._model,
            "instructions": SYSTEM_PROMPT,
            "input": build_user_prompt(question, format_evidence(evidence)),
            "max_output_tokens": self._max_output_tokens,
            "reasoning": {"effort": "low"},
            "text": {"verbosity": "medium"},
            "store": False,
        }
        if safety_identifier:
            request["safety_identifier"] = safety_identifier
        response = self._client.responses.create(**request)
        answer = response.output_text.strip()
        if not answer:
            raise RuntimeError("The generation model returned an empty answer.")
        return ensure_source_references(answer, evidence)
