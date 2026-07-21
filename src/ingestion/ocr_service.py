from __future__ import annotations

import base64

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Settings


class OpenAIOCRProvider:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_key)
        self._model = settings.openai_ocr_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    def extract_text(
        self,
        image_bytes: bytes,
        *,
        page_number: int,
        language: str | None,
    ) -> str:
        language_hint = {
            "ar": "The page is primarily Arabic.",
            "en": "The page is primarily English.",
        }.get(language or "", "Preserve every language visible on the page.")
        image_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
        response = self._client.responses.create(
            model=self._model,
            instructions=(
                "You are an OCR transcription engine. Return only the text visible in the image. "
                "Preserve headings, article numbers, paragraph order, punctuation, and line breaks. "
                "Do not translate, summarize, explain, or add Markdown fences. If a word is unclear, "
                "transcribe the most likely reading without commentary."
            ),
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Transcribe PDF page {page_number}. {language_hint}",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "high",
                        },
                    ],
                }
            ],
            max_output_tokens=6000,
            reasoning={"effort": "low"},
            store=False,
        )
        text = response.output_text.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return text
