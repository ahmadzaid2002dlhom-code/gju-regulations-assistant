from __future__ import annotations

import re
from dataclasses import dataclass


ARABIC_PATTERN = re.compile(r"[\u0600-\u06ff]")
LATIN_PATTERN = re.compile(r"[A-Za-z]")

TOPIC_TERMS: dict[str, tuple[str, ...]] = {
    "admission": ("admission", "admit", "قبول"),
    "registration": ("register", "registration", "course load", "تسجيل", "عبء"),
    "academic_warning": ("academic warning", "probation", "إنذار أكاديمي", "انذار"),
    "attendance": ("attendance", "absence", "miss lectures", "حضور", "غياب"),
    "graduation": ("graduation", "graduate", "final semester", "تخرج"),
    "german_year": ("german year", "germany year", "السنة الألمانية", "ألمانيا"),
    "discipline": ("discipline", "misconduct", "penalty", "عقوبة", "تأديب"),
    "graduate_studies": ("master", "phd", "graduate studies", "دراسات عليا", "ماجستير"),
    "fees": ("fee", "tuition", "payment", "رسوم", "دفع"),
    "change_of_major": ("change major", "transfer major", "تغيير التخصص", "تحويل التخصص"),
}


@dataclass(frozen=True, slots=True)
class QueryClassification:
    language: str
    topic: str | None
    suggested_document_type: str | None


def detect_language(text: str) -> str:
    has_arabic = bool(ARABIC_PATTERN.search(text))
    has_latin = bool(LATIN_PATTERN.search(text))
    if has_arabic and has_latin:
        return "mixed"
    if has_arabic:
        return "ar"
    return "en"


def classify_query(text: str) -> QueryClassification:
    language = detect_language(text)
    lowered = text.casefold()
    topic = next(
        (
            name
            for name, terms in TOPIC_TERMS.items()
            if any(term.casefold() in lowered for term in terms)
        ),
        None,
    )
    suggested_type = "german_year" if topic == "german_year" else None
    return QueryClassification(language, topic, suggested_type)
