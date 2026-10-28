from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from .channels import CHANNELS


REQUIRED_TEXT_FIELDS = ("editorial_text", "expected_spoken_text", "tts_input")
ELEVEN_V3_CHARACTER_LIMIT = 5_000


def validate_script_bundle(payload: dict[str, Any], *, require_cta: bool = False,
                           channel_cta_language: str | None = None,
                           engagement_cta_language: str | None = None) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_TEXT_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")

    tts_input = payload.get("tts_input")
    expected = payload.get("expected_spoken_text")
    if not isinstance(tts_input, str) or not isinstance(expected, str):
        return errors
    if len(tts_input) > ELEVEN_V3_CHARACTER_LIMIT:
        errors.append(
            f"tts_input exceeds the Eleven v3 limit of {ELEVEN_V3_CHARACTER_LIMIT} characters"
        )
    if tts_input.count("[") != tts_input.count("]"):
        errors.append("tts_input contains an unbalanced Eleven v3 audio tag")

    spoken_tts = re.sub(r"\[[^\]\r\n]+\]", " ", tts_input)
    similarity = SequenceMatcher(None, _canonical(expected), _canonical(spoken_tts)).ratio()
    if similarity < 0.97:
        errors.append(
            "tts_input spoken text does not match expected_spoken_text after removing audio tags"
        )
    if engagement_cta_language:
        channel = CHANNELS.get(engagement_cta_language)
        if not channel:
            errors.append(f"v9 CTA does not support language: {engagement_cta_language}")
            return errors
        cta = payload.get("cta")
        if not isinstance(cta, dict):
            errors.append("v9 script needs cta with spokenText, followPhrase and interactionPhrase")
        else:
            spoken, follow, interaction = (cta.get(name) for name in
                                            ("spokenText", "followPhrase", "interactionPhrase"))
            if any(not isinstance(value, str) or not value.strip() for value in (spoken, follow, interaction)):
                errors.append("v9 CTA fields spokenText, followPhrase and interactionPhrase must be non-empty")
            else:
                canonical_spoken = f" {_canonical(spoken)} "
                if not _canonical(expected).endswith(_canonical(spoken)):
                    errors.append("expected_spoken_text must end with cta.spokenText")
                if not _canonical(spoken_tts).endswith(_canonical(spoken)):
                    errors.append("tts_input must end with the spoken CTA after removing audio tags")
                if any(f" {_canonical(phrase)} " not in canonical_spoken for phrase in (follow, interaction)):
                    errors.append("CTA follow and interaction phrases must appear in spokenText")
                if f" {_canonical(channel['spoken'])} " not in canonical_spoken:
                    errors.append(f"CTA must say the full channel name: {channel['spoken']}")
                if any(name in cta for name in ("likePhrase", "subscribePhrase", "commentQuestion")):
                    errors.append("v9 CTA uses followPhrase and interactionPhrase, not button narration fields")
    elif channel_cta_language:
        channel = CHANNELS.get(channel_cta_language)
        if not channel:
            errors.append(f"v8 CTA does not support language: {channel_cta_language}")
            return errors
        cta = payload.get("cta")
        if not isinstance(cta, dict):
            errors.append("v8 script needs cta with spokenText, likePhrase and subscribePhrase")
        else:
            spoken, like, subscribe = (cta.get(name) for name in
                                       ("spokenText", "likePhrase", "subscribePhrase"))
            if any(not isinstance(value, str) or not value.strip() for value in (spoken, like, subscribe)):
                errors.append("v8 CTA fields spokenText, likePhrase and subscribePhrase must be non-empty")
            else:
                canonical_spoken = f" {_canonical(spoken)} "
                canonical_like = f" {_canonical(like)} "
                canonical_subscribe = f" {_canonical(subscribe)} "
                if not _canonical(expected).endswith(_canonical(spoken)):
                    errors.append("expected_spoken_text must end with cta.spokenText")
                if not _canonical(spoken_tts).endswith(_canonical(spoken)):
                    errors.append("tts_input must end with the spoken CTA after removing audio tags")
                if canonical_like not in canonical_spoken or canonical_subscribe not in canonical_spoken:
                    errors.append("CTA action phrases must appear exactly in spokenText")
                elif canonical_spoken.index(canonical_like) >= canonical_spoken.index(canonical_subscribe):
                    errors.append("CTA must ask for Like before Subscribe")
                if channel_cta_language == "vi":
                    if "thích" not in canonical_like.split() or "đăng ký" not in canonical_subscribe:
                        errors.append("v8 CTA needs spoken Thích and đăng ký actions")
                elif "like" not in canonical_like.split() or "subscribe" not in canonical_subscribe.split():
                    errors.append("v8 CTA needs spoken Like and Subscribe actions")
                if f" {_canonical(channel['spoken'])} " not in canonical_subscribe:
                    errors.append(f"subscribePhrase must say the full channel name: {channel['spoken']}")
                if "commentQuestion" in cta:
                    errors.append("v8 CTA does not use commentQuestion")
    elif require_cta:
        cta = payload.get("cta")
        if not isinstance(cta, dict):
            errors.append("v5 script needs cta with spokenText and commentQuestion")
        else:
            spoken = cta.get("spokenText")
            question = cta.get("commentQuestion")
            if not isinstance(spoken, str) or not spoken.strip() or not isinstance(question, str) or not question.strip():
                errors.append("cta spokenText and commentQuestion must be non-empty")
            else:
                if not _canonical(expected).endswith(_canonical(spoken)):
                    errors.append("expected_spoken_text must end with cta.spokenText")
                if _canonical(question) not in _canonical(spoken):
                    errors.append("cta.spokenText must include cta.commentQuestion")
    return errors


def _canonical(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())
