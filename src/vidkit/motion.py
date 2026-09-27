from __future__ import annotations

from typing import Any


def compile_events(scene: dict[str, Any], words: list[dict[str, Any]], fps: int = 30) -> list[dict[str, Any]]:
    entities = scene.get("entities", [])
    if not isinstance(entities, list) or any(not isinstance(item, dict) or not item.get("id") for item in entities):
        raise ValueError(f"Scene {scene['id']} entities must have stable ids")
    entity_ids = [item["id"] for item in entities]
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError(f"Scene {scene['id']} repeats an entity id")
    events = scene.get("events", [])
    if not isinstance(events, list):
        raise ValueError(f"Scene {scene['id']} events must be a list")
    by_id = {item.get("id"): item for item in events if isinstance(item, dict)}
    if len(by_id) != len(events) or None in by_id:
        raise ValueError(f"Scene {scene['id']} event ids must be unique")
    compiled: dict[str, dict[str, Any]] = {}
    visiting: set[str] = set()
    start_frame = round(scene["startMs"] / 1000 * fps)
    end_frame = round(scene["endMs"] / 1000 * fps)

    def resolve(event_id: str) -> dict[str, Any]:
        if event_id in compiled:
            return compiled[event_id]
        if event_id in visiting:
            raise ValueError(f"Scene {scene['id']} has cyclic motion events")
        if event_id not in by_id:
            raise ValueError(f"Scene {scene['id']} refers to missing event {event_id}")
        event = by_id[event_id]
        if event.get("entityId") not in entity_ids:
            raise ValueError(f"Scene {scene['id']} event {event_id} has unknown entity")
        visiting.add(event_id)
        duration = event.get("durationFrames", 0)
        hold = event.get("holdFrames", 0)
        offset = event.get("offsetFrames", 0)
        if any(not isinstance(value, int) or value < 0 for value in (duration, hold, offset)):
            raise ValueError(f"Scene {scene['id']} event {event_id} frame counts must be nonnegative integers")
        if "after" in event:
            predecessor = resolve(event["after"])
            frame = predecessor["endFrame"] + offset
        else:
            index = event.get("wordIndex")
            if not isinstance(index, int) or not scene["startWord"] <= index <= scene["endWord"]:
                raise ValueError(f"Scene {scene['id']} event {event_id} needs a word anchor in the scene")
            frame = round(float(words[index]["start"]) * fps) + offset
        if frame < start_frame or frame + duration + hold > end_frame:
            raise ValueError(f"Scene {scene['id']} event {event_id} does not fit its scene")
        result = {**event, "atFrame": frame, "endFrame": frame + duration + hold,
                  "atMs": round(frame / fps * 1000)}
        visiting.remove(event_id)
        compiled[event_id] = result
        return result

    return [resolve(event["id"]) for event in events]
