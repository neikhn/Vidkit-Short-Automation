from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Mode(StrEnum):
    REVIEW = "review"
    AUTOMATIC = "automatic"


class ArtifactKind(StrEnum):
    SOURCE = "source"
    SCRIPT = "script"
    BRIEF = "brief"
    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    ASSET_MANIFEST = "asset-manifest"
    STORYBOARD = "storyboard"
    CAPTION_PLAN = "caption-plan"
    SOUND_PLAN = "sound-plan"
    SOUND_ASSETS = "sound-assets"
    TIMELINE = "timeline"
    AUDIO_MIX = "audio-mix"
    SUBTITLE_SRT = "subtitle-srt"
    SUBTITLE_VTT = "subtitle-vtt"
    PREVIEW = "preview"
    QA_REPORT = "qa-report"
    APPROVAL = "approval"
    RENDER = "render"
    PUBLICATION = "publication"


class ArtifactStatus(StrEnum):
    PREPARED = "prepared"
    GENERATED = "generated"
    CHECKED = "checked"
    NEEDS_REVIEW = "needs-review"
    BLOCKED = "blocked"
    APPROVED = "approved"
    PUBLISHED = "published"
    INVALIDATED = "invalidated"


@dataclass(slots=True)
class TimedWord:
    text: str
    start: float
    end: float
    source_segment: int | None = None
    source_word: int | None = None
    kind: str = "word"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationFinding:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class CaptionToken:
    text: str
    start_ms: int
    end_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CaptionCue:
    text: str
    start_ms: int
    end_ms: int
    tokens: list[CaptionToken] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    start_word: int = 0
    end_word: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "startMs": self.start_ms,
            "endMs": self.end_ms,
            "tokens": [token.to_dict() for token in self.tokens],
            "lines": self.lines,
            "startWord": self.start_word,
            "endWord": self.end_word,
        }
