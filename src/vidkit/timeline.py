from __future__ import annotations

import unicodedata
from typing import Any

from .captions import build_caption_cues
from .motion import compile_events


SCENE_TYPES = ["hook", "screenshot", "steps", "takeaway", "brand-hook", "screenshot-focus",
               "api-response", "diagram-flow", "metric-breakdown"]


def build_draft_timeline(
    transcript: dict[str, Any],
    title: str,
    language: str,
    audio_src: str,
) -> dict[str, Any]:
    words = transcript.get("words", [])
    if not words:
        raise ValueError("Cannot build a timeline without timed words")
    cues = build_caption_cues(words)
    duration_ms = _duration_ms(transcript, words)
    scenes: list[dict[str, Any]] = []
    scene_count = min(len(SCENE_TYPES), max(1, len(cues)))
    cues_per_scene = max(1, (len(cues) + scene_count - 1) // scene_count)
    for index in range(scene_count):
        owned = cues[index * cues_per_scene : (index + 1) * cues_per_scene]
        if not owned:
            continue
        scenes.append(
            {
                "id": f"scene-{index + 1}",
                "layout": SCENE_TYPES[index],
                "purpose": "technical-draft",
                "title": _nfc(title if index == 0 else owned[0].text),
                "body": "",
                "startMs": 0 if index == 0 else owned[0].start_ms,
                "endMs": duration_ms if index == scene_count - 1 else owned[-1].end_ms,
                "status": "provisional",
                "asset": None,
            }
        )
    return _timeline_payload(
        language, title, audio_src, duration_ms, cues, scenes, "technical-draft", []
    )


def compile_storyboard(
    transcript: dict[str, Any],
    storyboard: dict[str, Any],
    asset_manifest: dict[str, Any],
    title: str,
    language: str,
    audio_src: str,
    caption_plan: dict[str, Any] | None = None,
    library_entries: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    words = transcript.get("words", [])
    if not words:
        raise ValueError("Cannot build a timeline without timed words")
    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Storyboard must contain at least one scene")
    assets = {item.get("id"): item for item in asset_manifest.get("assets", [])}
    compiled: list[dict[str, Any]] = []
    missing_assets: list[str] = []
    previous_end = -1
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index + 1} must be an object")
        layout = str(scene.get("layout", ""))
        if layout not in SCENE_TYPES and not (storyboard.get("schemaVersion") == 4 and layout == "custom"):
            raise ValueError(f"Scene {index + 1} has unsupported layout: {layout}")
        component_id = str(scene.get("component", {"hook": "brand-hook", "screenshot": "screenshot-focus",
                                                   "steps": "diagram-flow"}.get(layout, layout)))
        component_version = str(scene.get("componentVersion", "1.0.0"))
        component_entry = next((item for item in (library_entries or [])
                                if item.get("id") == component_id and item.get("version") == component_version
                                and item.get("kind") == "component"), None)
        if library_entries is not None and component_entry is None:
            raise ValueError(f"Scene {index + 1} references unknown component {component_id}@{component_version}")
        if component_entry and component_entry.get("status") == "candidate":
            if not component_entry.get("previewValid"):
                raise ValueError(f"Scene {index + 1} candidate requires a rendered library preview")
        if storyboard.get("schemaVersion") == 4 and component_entry and component_entry.get("entrypoint"):
            props = scene.get("componentProps", {})
            if not isinstance(props, dict):
                raise ValueError(f"Scene {index + 1} componentProps must be an object")
            missing_props = [key for key, meaning in component_entry.get("propsSchema", {}).items()
                             if meaning != "optional" and key not in props]
            if missing_props:
                raise ValueError(f"Scene {index + 1} component is missing props: {', '.join(missing_props)}")
        start_index = _anchor_index(scene.get("startAnchor"), words, "start", index)
        end_index = _anchor_index(scene.get("endAnchor"), words, "end", index)
        if start_index > end_index:
            raise ValueError(f"Scene {index + 1} starts after it ends")
        if index == 0 and start_index != 0:
            raise ValueError("Storyboard must start at word 0")
        if start_index != previous_end + 1:
            raise ValueError(f"Scene {index + 1} must begin at word {previous_end + 1}")
        previous_end = end_index
        asset_id = scene.get("assetId")
        required_asset = bool(scene.get("assetRequired", layout in {"screenshot", "screenshot-focus"}))
        asset = assets.get(asset_id) if asset_id else None
        if required_asset and asset is None:
            missing_assets.append(str(asset_id or f"scene:{scene.get('id', index + 1)}"))
        support_asset_ids = scene.get("supportAssetIds", [])
        if not isinstance(support_asset_ids, list) or any(not isinstance(value, str) for value in support_asset_ids):
            raise ValueError(f"Scene {index + 1} supportAssetIds must be a list of asset IDs")
        support_assets = []
        for support_id in support_asset_ids:
            support_asset = assets.get(support_id)
            if support_asset is None:
                missing_assets.append(support_id)
            else:
                support_assets.append(support_asset)
        compiled.append(
            {
                "id": str(scene.get("id") or f"scene-{index + 1}"),
                "layout": layout,
                "purpose": _nfc(str(scene.get("purpose") or "")),
                "title": _nfc(str(scene.get("title") or "")),
                "body": _nfc(str(scene.get("body") or "")),
                "startWord": start_index,
                "endWord": end_index,
                "startMs": 0 if index == 0 else round(float(words[start_index]["start"]) * 1000),
                "endMs": 0,
                "status": "blocked" if required_asset and asset is None else "checked",
                "asset": asset,
                "supportAssets": support_assets,
                "assetRequired": required_asset,
                "crop": _validate_crop(scene.get("crop"), index),
                "callout": scene.get("callout"),
                "component": component_entry.get("baseComponent", component_id) if component_entry else component_id,
                "componentId": component_id,
                "componentVersion": component_version,
                "componentProps": scene.get("componentProps", {}),
                "entities": scene.get("entities", []),
                "continuityGroup": scene.get("continuityGroup"),
                "outgoing": scene.get("outgoing"),
                "development": scene.get("development"),
                "referenceIds": scene.get("referenceIds", []),
                "focusRect": scene.get("focusRect"),
                "claimIds": scene.get("claimIds", []),
                "motion": _compile_motion(
                    {**(component_entry.get("defaults", {}).get("motion", {}) if component_entry else {}),
                     **scene.get("motion", {})},
                    words, start_index, end_index, index,
                ),
            }
        )
    if previous_end != len(words) - 1:
        raise ValueError(f"Storyboard must end at word {len(words) - 1}")
    duration_ms = _duration_ms(transcript, words)
    for index, scene in enumerate(compiled):
        scene["endMs"] = compiled[index + 1]["startMs"] if index + 1 < len(compiled) else duration_ms
        if storyboard.get("schemaVersion") == 4:
            scene["absoluteStartFrame"] = round(scene["startMs"] / 1000 * 30)
            scene["events"] = compile_events({**scene, "events": scenes[index].get("events", [])}, words)
            group = scene.get("continuityGroup")
            if group:
                previous = compiled[index - 1] if index else None
                if previous and previous.get("continuityGroup") == group:
                    current_ids = {entity["id"] for entity in scene["entities"]}
                    previous_ids = {entity["id"] for entity in previous["entities"]}
                    if not current_ids & previous_ids:
                        raise ValueError(f"Scene {scene['id']} continuity group needs a shared entity id")
                    scene["continuityStartFrame"] = previous["continuityStartFrame"]
                else:
                    if any(prior.get("continuityGroup") == group for prior in compiled[:index]):
                        raise ValueError(f"Scene {scene['id']} continuity group is not adjacent")
                    scene["continuityStartFrame"] = scene["absoluteStartFrame"]
    cues = build_caption_cues(words, plan=caption_plan)
    asset_warnings = list(
        dict.fromkeys(
            f"{scene['asset']['id']}: {warning}"
            for scene in compiled
            if scene.get("asset")
            for warning in scene["asset"].get("qualityWarnings", [])
        )
    )
    for scene in compiled:
        asset = scene.get("asset")
        if asset and scene["layout"] in {"screenshot", "screenshot-focus"} and scene.get("motion", {}).get("mode") != "jev-article-tour":
            crop = scene["crop"]
            crop_aspect = crop["width"] * asset["width"] / (crop["height"] * asset["height"])
            panel_aspect = 948 / 890
            if crop_aspect > panel_aspect * 1.35 or crop_aspect < panel_aspect / 1.35:
                asset_warnings.append(
                    f"{asset['id']}: crop aspect differs from portrait panel; cover may clip the selected region"
                )
    timeline = _timeline_payload(
        language,
        title,
        audio_src,
        duration_ms,
        cues,
        compiled,
        "blocked" if missing_assets else "checked",
        missing_assets,
    )
    sound_cues = storyboard.get("sfx", [])
    if not isinstance(sound_cues, list):
        raise ValueError("Storyboard sfx must be a list")
    timeline["sfx"] = []
    for cue in sound_cues:
        if not isinstance(cue, dict) or cue.get("type") != "whoosh":
            raise ValueError("Storyboard sfx only supports whoosh cues")
        word_index = cue.get("wordIndex")
        if not isinstance(word_index, int) or not 0 <= word_index < len(words):
            raise ValueError("Storyboard sfx wordIndex must be in the transcript")
        timeline["sfx"].append({"type": "whoosh", "wordIndex": word_index,
                                "atMs": round(float(words[word_index]["start"]) * 1000)})
    timeline["assetWarnings"] = asset_warnings
    timeline["theme"] = storyboard.get("theme", "dark-grid")
    theme_entry = next((item for item in (library_entries or []) if item.get("id") == timeline["theme"]
                        and item.get("kind") == "theme"), None)
    if library_entries is not None and theme_entry is None:
        raise ValueError(f"Unknown theme: {timeline['theme']}")
    if theme_entry and theme_entry.get("status") == "candidate" and not theme_entry.get("previewValid"):
        raise ValueError(f"Theme {timeline['theme']} candidate requires a rendered library preview")
    timeline["themeLock"] = {"id": timeline["theme"], "version": theme_entry["version"],
                             "sha256": theme_entry["sha256"]} if theme_entry else None
    if theme_entry and theme_entry.get("style"):
        timeline["themeData"] = theme_entry["style"]
    timeline["componentLocks"] = [
        {"id": scene["componentId"], "version": scene["componentVersion"],
         "sha256": next((item.get("sha256") for item in (library_entries or [])
                         if item.get("id") == scene["componentId"] and item.get("version") == scene["componentVersion"]), None)}
        for scene in compiled
    ]
    effect_ids = {"bits-gradient-transition"}
    if any(scene["component"] == "brand-hook" for scene in compiled):
        effect_ids.add("bits-animated-text")
    if any(scene["component"] == "metric-breakdown" for scene in compiled):
        effect_ids.add("bits-animated-counter")
    timeline["effectLocks"] = [
        {"id": item["id"], "version": item["version"], "sha256": item["sha256"]}
        for item in (library_entries or []) if item.get("id") in effect_ids and item.get("kind") == "effect"
    ]
    timeline["claimToScene"] = {
        claim: scene["id"] for scene in compiled for claim in scene["claimIds"]
    }
    return timeline, missing_assets


def validate_storyboard_shape(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schemaVersion") not in {1, 3, 4}:
        errors.append("schemaVersion must be 1, 3 or 4")
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty list")
        return errors
    seen: set[str] = set()
    for index, scene in enumerate(scenes):
        label = f"scene {index + 1}"
        if not isinstance(scene, dict):
            errors.append(f"{label} must be an object")
            continue
        scene_id = str(scene.get("id") or "")
        if not scene_id:
            errors.append(f"{label} id is required")
        elif scene_id in seen:
            errors.append(f"duplicate scene id: {scene_id}")
        seen.add(scene_id)
        if scene.get("layout") not in SCENE_TYPES and not (payload.get("schemaVersion") == 4 and scene.get("layout") == "custom"):
            errors.append(f"{label} layout must be one of: {', '.join(SCENE_TYPES)}")
        if not isinstance(scene.get("title"), str) or not scene["title"].strip():
            errors.append(f"{label} title is required")
        for anchor_name in ("startAnchor", "endAnchor"):
            anchor = scene.get(anchor_name)
            if not isinstance(anchor, dict) or not isinstance(anchor.get("wordIndex"), int):
                errors.append(f"{label} {anchor_name}.wordIndex is required")
        if scene.get("assetRequired") and not scene.get("assetId"):
            errors.append(f"{label} requires assetId")
        if payload.get("schemaVersion") in {3, 4}:
            if not isinstance(scene.get("claimIds", []), list):
                errors.append(f"{label} claimIds must be a list")
            if not isinstance(scene.get("motion", {}), dict):
                errors.append(f"{label} motion must be an object")
        if payload.get("schemaVersion") == 4:
            if scene.get("layout") == "custom" and not scene.get("component"):
                errors.append(f"{label} custom layout needs component")
            if not isinstance(scene.get("componentProps", {}), dict):
                errors.append(f"{label} componentProps must be an object")
            if not isinstance(scene.get("development"), dict) or not all(
                scene["development"].get(key) for key in ("understanding", "object", "action", "result", "connection")
            ):
                errors.append(f"{label} development needs understanding, object, action, result, connection")
        try:
            _validate_crop(scene.get("crop"), index)
        except (TypeError, ValueError) as exc:
            errors.append(str(exc))
    return errors


def _anchor_index(anchor: Any, words: list[dict[str, Any]], name: str, scene_index: int) -> int:
    if not isinstance(anchor, dict) or not isinstance(anchor.get("wordIndex"), int):
        raise ValueError(f"Scene {scene_index + 1} {name}Anchor.wordIndex is required")
    word_index = anchor["wordIndex"]
    if word_index < 0 or word_index >= len(words):
        raise ValueError(f"Scene {scene_index + 1} {name}Anchor is outside the transcript")
    expected = anchor.get("text")
    if expected and _canonical(str(expected)) != _canonical(str(words[word_index].get("text", ""))):
        raise ValueError(f"Scene {scene_index + 1} {name}Anchor text does not match word {word_index}")
    return word_index


def _validate_crop(crop: Any, scene_index: int) -> dict[str, float]:
    if crop is None:
        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    if not isinstance(crop, dict):
        raise ValueError(f"Scene {scene_index + 1} crop must be an object")
    result = {key: float(crop.get(key, default)) for key, default in (("x", 0), ("y", 0), ("width", 1), ("height", 1))}
    if any(value < 0 or value > 1 for value in result.values()):
        raise ValueError(f"Scene {scene_index + 1} crop values must be between 0 and 1")
    if result["width"] <= 0 or result["height"] <= 0 or result["x"] + result["width"] > 1 or result["y"] + result["height"] > 1:
        raise ValueError(f"Scene {scene_index + 1} crop rectangle is invalid")
    return result


def _compile_motion(motion: dict[str, Any], words: list[dict[str, Any]],
                    start: int, end: int, scene_index: int) -> dict[str, Any]:
    result = dict(motion)
    cues = result.get("cues", [])
    if not isinstance(cues, list):
        raise ValueError(f"Scene {scene_index + 1} motion.cues must be a list")
    compiled = []
    for cue in cues:
        anchor = cue.get("wordIndex") if isinstance(cue, dict) else None
        if not isinstance(anchor, int) or not start <= anchor <= end:
            raise ValueError(f"Scene {scene_index + 1} motion cue wordIndex must be in scene")
        compiled.append({**cue, "atMs": round(float(words[anchor]["start"]) * 1000)})
    result["cues"] = compiled
    return result


def _timeline_payload(
    language: str,
    title: str,
    audio_src: str,
    duration_ms: int,
    cues: list[Any],
    scenes: list[dict[str, Any]],
    storyboard_status: str,
    missing_assets: list[str],
) -> dict[str, Any]:
    return {
        "schemaVersion": 2,
        "language": language,
        "title": _nfc(title),
        "audioSrc": audio_src,
        "durationSeconds": duration_ms / 1000,
        "captions": [cue.to_dict() for cue in cues],
        "scenes": scenes,
        "storyboardStatus": storyboard_status,
        "missingAssets": missing_assets,
        "assetWarnings": [],
        "safeArea": {"top": 88, "right": 162, "bottom": 260, "left": 162},
    }


def _duration_ms(transcript: dict[str, Any], words: list[dict[str, Any]]) -> int:
    audio_duration = transcript.get("audio", {}).get("duration_seconds")
    if isinstance(audio_duration, (int, float)) and audio_duration > 0:
        return max(round(float(audio_duration) * 1000), round(float(words[-1]["end"]) * 1000))
    return max(round(float(words[-1]["end"]) * 1000) + 350, 1000)


def _canonical(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)
