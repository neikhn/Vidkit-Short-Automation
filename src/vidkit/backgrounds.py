"""Layered backgrounds for v10; the legacy backgroundId path stays separate."""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

KINDS = {"background-pattern", "background-effect"}


def normalize(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("patternId"), str) or not value["patternId"].strip():
        raise ValueError("v10 background needs a non-empty patternId")
    effects = value.get("effectIds", [])
    if (not isinstance(effects, list) or any(not isinstance(item, str) or not item.strip() for item in effects)
            or len(effects) != len(set(effects))):
        raise ValueError("background.effectIds must contain unique non-empty IDs")
    result = {"patternId": value["patternId"], "effectIds": effects}
    ranges = {"density": (.5, 2), "lineWidth": (.5, 6), "opacity": (0, 1), "motionIntensity": (0, 1)}

    def settings(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Background settings must be an object")
        for name, val in data.items():
            if name == "color":
                if not isinstance(val, str) or not val.strip():
                    raise ValueError("Background color must be a non-empty CSS color")
            elif (name not in ranges or isinstance(val, bool) or not isinstance(val, (int, float))
                  or not math.isfinite(val) or not ranges[name][0] <= val <= ranges[name][1]):
                raise ValueError(f"Invalid background setting: {name}")
        return data

    if "patternProps" in value:
        result["patternProps"] = settings(value["patternProps"])
    if "effectProps" in value:
        if not isinstance(value["effectProps"], dict) or not set(value["effectProps"]) <= set(effects):
            raise ValueError("effectProps must refer to selected effect IDs")
        result["effectProps"] = {key: settings(data) for key, data in value["effectProps"].items()}
    return deepcopy(result)


def resolve(value: Any, available: list[dict[str, Any]], *, require_motion: bool = True) -> dict[str, Any]:
    config = normalize(value)
    layers = []
    choices = [(config["patternId"], "background-pattern", config.get("patternProps", {}))]
    choices += [(key, "background-effect", config.get("effectProps", {}).get(key, {})) for key in config["effectIds"]]
    for entry_id, kind, props in choices:
        item = next((item for item in reversed(available) if item.get("id") == entry_id and item.get("kind") == kind), None)
        if not item or not item.get("entrypoint"):
            raise ValueError(f"Unknown {kind}: {entry_id}")
        if require_motion and item.get("status") == "candidate" and not item.get("previewValid"):
            raise ValueError(f"Background layer {entry_id} needs a current motion preview; a still is insufficient")
        period = item.get("loopSeconds")
        if isinstance(period, bool) or not isinstance(period, (int, float)) or not 2 <= period <= 30:
            raise ValueError(f"Background layer {entry_id} needs loopSeconds between 2 and 30")
        layers.append({"id": entry_id, "kind": kind, "version": item["version"], "sha256": item["sha256"],
                       "loopSeconds": period, "settings": props})
    return {"background": config, "backgroundLayers": layers}


def selection(data: dict[str, Any]) -> Any:
    return normalize(data["background"]) if data.get("background") is not None else data.get("backgroundId")


def selection_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {"background": data["background"]} if data.get("background") is not None else {"backgroundId": data.get("backgroundId")}


def evidence_matches(evidence: dict[str, Any], brief: dict[str, Any], version: int) -> bool:
    if version >= 10 or brief.get("background") is not None:
        config = normalize(brief.get("background"))
        layers = evidence.get("backgroundLayers")
        expected = [(config["patternId"], "background-pattern"), *[(key, "background-effect") for key in config["effectIds"]]]
        return (evidence.get("background") == config and isinstance(layers, list)
                and all(isinstance(layer, dict) for layer in layers)
                and [(layer.get("id"), layer.get("kind")) for layer in layers] == expected)
    return version < 7 or (evidence.get("backgroundLock") or {}).get("id") == brief.get("backgroundId")


def lock_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {key: data.get(key) for key in ("themeLock", "backgroundLock", "backgroundLayers")}
