from __future__ import annotations

import re
from dataclasses import dataclass

from src.models import DetectedSection, ExtractedPage


ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ARTICLE_PATTERN = re.compile(
    r"(?im)^\s*(?:Article|المادة|ةالماد)[\s():.\-–—]*([0-9٠-٩]+)[\s():.\-–—]*"
)
CHAPTER_PATTERN = re.compile(
    r"(?im)^\s*(?:Chapter|الفصل)\s+([^\n:]{1,80})"
)
SECTION_PATTERN = re.compile(
    r"(?im)^\s*(?:Section|القسم)\s+([^\n:]{1,80})"
)


def normalize_number(value: str) -> str:
    return value.translate(ARABIC_DIGITS)


@dataclass(slots=True)
class _HeadingEvent:
    page: int
    position: int
    title: str
    section_type: str
    level: int
    article_number: str | None = None
    parent_key: str | None = None
    local_key: str = ""


def _page_events(page: ExtractedPage) -> list[_HeadingEvent]:
    events: list[_HeadingEvent] = []
    for pattern, section_type, level in (
        (CHAPTER_PATTERN, "chapter", 1),
        (SECTION_PATTERN, "section", 2),
    ):
        for match in pattern.finditer(page.page_text):
            label = match.group(0).strip()
            events.append(
                _HeadingEvent(
                    page=page.pdf_page_number,
                    position=match.start(),
                    title=label,
                    section_type=section_type,
                    level=level,
                )
            )

    for match in ARTICLE_PATTERN.finditer(page.page_text):
        number = normalize_number(match.group(1))
        events.append(
            _HeadingEvent(
                page=page.pdf_page_number,
                position=match.start(),
                title=f"Article {number}",
                section_type="article",
                level=3,
                article_number=number,
            )
        )
    return sorted(events, key=lambda event: event.position)


def detect_sections(pages: list[ExtractedPage]) -> list[DetectedSection]:
    if not pages:
        return []

    events: list[_HeadingEvent] = []
    active_parents: dict[int, str] = {}
    counters = {"chapter": 0, "section": 0, "article": 0}

    for page in pages:
        for event in _page_events(page):
            counters[event.section_type] += 1
            event.local_key = (
                f"{event.section_type}-{counters[event.section_type]}-p{event.page}"
            )
            parent_levels = [level for level in active_parents if level < event.level]
            if parent_levels:
                event.parent_key = active_parents[max(parent_levels)]
            active_parents[event.level] = event.local_key
            for level in [value for value in active_parents if value > event.level]:
                active_parents.pop(level, None)
            events.append(event)

    last_page = pages[-1].pdf_page_number
    sections: list[DetectedSection] = []
    for index, event in enumerate(events):
        later = next(
            (
                candidate
                for candidate in events[index + 1 :]
                if candidate.level <= event.level
            ),
            None,
        )
        page_end = later.page if later else last_page
        sections.append(
            DetectedSection(
                local_key=event.local_key,
                title=event.title,
                section_type=event.section_type,
                hierarchy_level=event.level,
                page_start=event.page,
                page_end=max(event.page, page_end),
                article_number=event.article_number,
                parent_local_key=event.parent_key,
            )
        )
    return sections
