"""Run three new v4 fixture jobs without calling a paid service.

Run from the repository root: .venv/Scripts/python tests/smoke_v4.py
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

from vidkit import visuals, workflow
from vidkit.cli import _concept_preview, _remotion, _timeline
from vidkit.models import ArtifactKind as K, ArtifactStatus as S, Mode
from vidkit.storage import Workspace


ROOT = Path(__file__).resolve().parents[1]
BEAT = {"understanding": "See what the claim means", "object": "One result",
        "action": "Reveal the result", "result": "The result is readable",
        "connection": "Carry it into the next beat"}


def save(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    workspace = Workspace(ROOT)
    workspace.initialize()
    source = workspace.cache_root / "v4-smoke-input"
    source.mkdir(parents=True, exist_ok=True)
    (source / "ProductPulse.tsx").write_text(
        "import React from 'react';\n"
        "import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';\n"
        "export default function ProductPulse({scene,theme}:{scene:any;theme:any}){\n"
        "const f=useCurrentFrame();const grow=interpolate(f,[0,25],[.6,1],{extrapolateRight:'clamp'});\n"
        "return <AbsoluteFill style={{display:'grid',placeItems:'center',padding:90,background:theme.background,color:theme.text}}><div style={{transform:`scale(${grow})`,padding:70,borderRadius:36,background:theme.surface,fontSize:72,fontWeight:900}}>{scene.title}</div></AbsoluteFill>}\n",
        encoding="utf-8",
    )
    save(source / "fixture.json", {"schemaVersion": 4, "language": "en", "title": "Product pulse",
        "audioSrc": "", "durationSeconds": 5, "captions": [], "theme": "dark-grid",
        "scenes": [{"id": "pulse", "layout": "custom", "componentId": "product-pulse",
                    "title": "A new product", "body": "", "startMs": 0, "endMs": 5000}]})
    save(source / "manifest.json", {"kind": "component", "id": "product-pulse", "version": "1.0.0",
        "description": "A job-specific visual hook", "propsSchema": {},
        "entrypoint": "ProductPulse.tsx", "fixture": "fixture.json"})

    cases = [
        ("product-introduction", "product-pulse", {}, "custom"),
        ("mechanism-explanation", "branch-flow", {"sourceNode": "Request", "branches": ["Choice", "Score"]}, "custom"),
        ("numeric-comparison", "range-log-chart", {"values": [{"label": "A", "value": 70},
            {"label": "B", "value": 500}], "unit": "ms", "source": "Synthetic fixture", "scale": "log"}, "custom"),
    ]
    for name, component, component_props, layout in cases:
        title = f"V4 fixture {name}"
        existing = next((item for item in workspace.list_jobs() if item["topic"] == title), None)
        job = existing["id"] if existing else workspace.create_job(title, ["en"], Mode.AUTOMATIC)
        print(f"{name}: {job}", flush=True)
        if not workspace.latest_artifact(job, K.SOURCE, None):
            workspace.add_json_artifact(job, None, K.SOURCE, {"claims": [{"id": "fixture-claim",
                "statement": "Synthetic validation claim", "sourceUrl": "https://example.com/fixture",
                "publishedAt": None, "retrievedAt": "2026-09-26", "uncertainty": "Fixture only"}]}, S.CHECKED)
        if not workspace.latest_artifact(job, K.SCRIPT, "en"):
            workspace.add_json_artifact(job, "en", K.SCRIPT, {"title": name, "editorial_text": "First next done.",
                "expected_spoken_text": "First next done.", "tts_input": "First next done."}, S.CHECKED)
        if name == "product-introduction":
            if not visuals.entries(workspace, job, "en"):
                visuals.add(workspace, job, "en", source / "manifest.json")
            visuals.preview(workspace, job, "en", "product-pulse")
        concept = {"angle": "Explain one fixture claim", "theme": "dark-grid", "hook": "A simple claim",
            "visualStrategy": "Reveal one object then its consequence",
            "beats": [{"id": "beat-1", "development": BEAT, "approach": "custom" if name == "product-introduction" else "reuse"}],
            "explanationAlternatives": ["Reveal", "Compare"], "chosenExplanation": "Reveal",
            "conceptPreview": {"scenes": [
                {"id": "hook", "role": "hook", "layout": layout, "component": component,
                 "title": "First", "body": "", "componentProps": component_props, "startMs": 0, "endMs": 5000},
                {"id": "evidence", "role": "evidence", "layout": layout, "component": component,
                 "title": "Next", "body": "", "componentProps": component_props, "startMs": 5000, "endMs": 10000},
                {"id": "takeaway", "role": "takeaway", "layout": "takeaway", "component": "takeaway",
                 "title": "Done", "body": "", "startMs": 10000, "endMs": 13000},
            ]}}
        brief = save(source / f"{name}-brief.json", concept)
        workflow.add_brief(workspace, job, "en", brief)
        if _concept_preview(workspace, job, "en", None):
            raise RuntimeError("Concept render failed")
        audio = source / f"{name}.wav"
        with wave.open(str(audio), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b"\0\0" * 24000 * 4)
        workspace.add_file_artifact(job, "en", K.AUDIO, audio, S.CHECKED)
        words = [{"text": token, "start": index * 1.25, "end": index * 1.25 + .4}
                 for index, token in enumerate(["First", "next", "done."])]
        workspace.add_json_artifact(job, "en", K.TRANSCRIPT,
                                    {"text": "First next done.", "words": words, "durationSeconds": 4},
                                    S.CHECKED, metadata={"variant": "normalized", "fixture": True})
        storyboard = {"schemaVersion": 4, "language": "en", "theme": "dark-grid", "scenes": []}
        for index, word in enumerate(words):
            scene = {"id": f"scene-{index}", "layout": layout if index == 1 else "takeaway",
                "component": component if index == 1 else "takeaway", "title": word["text"],
                "componentProps": component_props if index == 1 else {}, "development": BEAT,
                "startAnchor": {"wordIndex": index}, "endAnchor": {"wordIndex": index}}
            storyboard["scenes"].append(scene)
        workspace.add_json_artifact(job, "en", K.STORYBOARD, storyboard, S.CHECKED)
        _timeline(workspace, job, "en", False)
        if _remotion(workspace, job, "en", "preview"):
            raise RuntimeError("Video preview failed")
        workflow.make_qa(workspace, job, "en")
        if _remotion(workspace, job, "en", "render"):
            raise RuntimeError("Video export failed")
        print(f"complete: {job}", flush=True)


if __name__ == "__main__":
    main()
