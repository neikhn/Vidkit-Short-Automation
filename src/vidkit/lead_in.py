from __future__ import annotations

from typing import Any


def apply_lead_in(timeline: dict[str, Any], lead_in_ms: int) -> None:
    """Offset presentation timing while retaining clean narration/STT source time."""
    if isinstance(lead_in_ms, bool) or not isinstance(lead_in_ms, int) or not 0 <= lead_in_ms <= 5000 or lead_in_ms % 100:
        raise ValueError("leadInMs must be 0–5000 in 100ms steps (whole 30fps frames)")
    if not lead_in_ms:
        return
    if timeline.get("leadInMs"):
        raise ValueError("Opening lead-in was already applied")
    frames = lead_in_ms * 30 // 1000
    timeline["leadInMs"] = lead_in_ms
    timeline["audioStartMs"] = lead_in_ms
    timeline["durationSeconds"] += lead_in_ms / 1000
    def offset_fields(item, keys, amount):
        for key in keys:
            if key in item:
                item[key] += amount
    for index, scene in enumerate(timeline["scenes"]):
        offset_fields(scene, ["startMs", "endMs"], lead_in_ms)
        offset_fields(scene, ["absoluteStartFrame", "continuityStartFrame"], frames)
        for event in scene.get("events", []):
            offset_fields(event, ["atMs", "endMs"], lead_in_ms)
            offset_fields(event, ["atFrame", "endFrame"], frames)
        for cue in scene.get("motion", {}).get("cues", []):
            offset_fields(cue, ["atMs"], lead_in_ms)
        if index == 0:
            scene["startMs"] = 0  # The first visual also fills the silent opening.
    for caption in timeline["captions"]:
        offset_fields(caption, ["startMs", "endMs"], lead_in_ms)
        for token in caption.get("tokens", []):
            offset_fields(token, ["startMs", "endMs", "start_ms", "end_ms"], lead_in_ms)
    for track in timeline.get("soundTracks", []):
        offset_fields(track, ["startMs", "endMs"], lead_in_ms)
        for point in track.get("envelope", []):
            offset_fields(point, ["atMs"], lead_in_ms)
    for cue in timeline.get("sfx", []):
        offset_fields(cue, ["atMs"], lead_in_ms)
