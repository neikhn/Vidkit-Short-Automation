"""Render a new deterministic sound fixture; no paid service calls.

Run from the repository root: .venv/Scripts/python tests/smoke_sound.py
"""
from __future__ import annotations

import json
import math
import struct
import wave
from array import array
from pathlib import Path

from vidkit import sound, workflow
from vidkit.cli import _audio_preview, _remotion, _timeline
from vidkit.models import ArtifactKind as K, ArtifactStatus as S, Mode
from vidkit.storage import Workspace


ROOT = Path(__file__).resolve().parents[1]


def tone(path: Path, duration: float, frequency: float, amplitude: int, intervals=None):
    sample_rate = 24000
    data = array("h")
    for index in range(round(duration * sample_rate)):
        time = index / sample_rate
        active = intervals is None or any(start <= time <= end for start, end in intervals)
        data.append(round(amplitude * math.sin(2 * math.pi * frequency * time)) if active else 0)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(data.tobytes())


def magnitude(path: Path, time: float, frequency: float) -> float:
    with wave.open(str(path), "rb") as audio:
        rate, channels, width = audio.getframerate(), audio.getnchannels(), audio.getsampwidth()
        if width != 2:
            raise ValueError("Smoke measurement expects PCM16 WAV")
        audio.setpos(round(time * rate))
        frames = audio.readframes(round(rate * .1))
    samples = struct.unpack("<" + "h" * (len(frames) // 2), frames)[::channels]
    real = sum(value * math.cos(2 * math.pi * frequency * i / rate) for i, value in enumerate(samples))
    imag = sum(value * math.sin(2 * math.pi * frequency * i / rate) for i, value in enumerate(samples))
    return 2 * math.hypot(real, imag) / len(samples)


def main():
    workspace = Workspace(ROOT)
    workspace.initialize()
    job = workspace.create_job("Sound mix regression fixture", ["en"], Mode.AUTOMATIC)
    print(f"job: {job}", flush=True)
    source = workspace.cache_root / "sound-smoke" / job
    source.mkdir(parents=True)
    tone(source / "narration.wav", 6, 220, 2000, [(.5, 1.4), (2.5, 2.8), (4, 4.4)])
    tone(source / "music.wav", 2.5, 440, 5000)
    tone(source / "ping.wav", .5, 880, 4000)
    workspace.add_json_artifact(job, None, K.SOURCE, {"claims": [{"id": "test",
        "statement": "Synthetic audio fixture", "sourceUrl": "fixture://sound-test"}]}, S.CHECKED)
    workspace.add_json_artifact(job, "en", K.SCRIPT, {"title": "Audio fixture", "expected_spoken_text": "First next result last"}, S.CHECKED)
    workspace.add_json_artifact(job, "en", K.BRIEF, {"theme": "dark-grid", "soundDirection": {
        "music": "Synthetic 440Hz test loop", "sfx": "Synthetic 880Hz timing marker"}}, S.CHECKED)
    audio = workspace.add_file_artifact(job, "en", K.AUDIO, source / "narration.wav", S.CHECKED)
    words = [{"text": text, "start": start, "end": end} for text, start, end in
             [("First", .5, .8), ("next", 1, 1.4), ("result", 2.5, 2.8), ("last", 4, 4.4)]]
    workspace.add_json_artifact(job, "en", K.TRANSCRIPT, {"words": words, "audio": {
        "duration_seconds": 6, "sha256": audio["sha256"]}}, S.CHECKED, metadata={"variant": "normalized", "fixture": True})
    workspace.add_json_artifact(job, "en", K.STORYBOARD, {"schemaVersion": 4, "language": "en",
        "theme": "dark-grid", "scenes": [{"id": "test", "layout": "takeaway", "title": "Audio mix fixture",
        "body": "Synthetic signals: voice / music / effect", "claimIds": ["test"], "startAnchor": {"wordIndex": 0},
        "endAnchor": {"wordIndex": 3}, "development": {"understanding": "Check audio wiring", "object": "Signals",
        "action": "Duck background under voice", "result": "Lower music during voice", "connection": "Review measured mix"}}]}, S.CHECKED)
    for kind, name in (("sfx", "ping"), ("music", "bed")):
        sound.register_asset(workspace, job, source / ("ping.wav" if kind == "sfx" else "music.wav"), name, kind,
                             {"description": "Synthetic test tone", "source": "local regression fixture", "usageBasis": "generated test signal"})
    plan = {"schemaVersion": 1, "music": {"id": "bed", "assetId": "bed", "purpose": "Verify ducking and loops",
            "gainDb": -12, "duckDb": -10, "loop": True, "crossfadeMs": 250, "fadeInMs": 200, "fadeOutMs": 400},
            "sfx": [{"id": "ping", "assetId": "ping", "purpose": "Verify anchored effect", "wordIndex": 2,
                     "impactMs": 100, "gainDb": -12, "fadeInMs": 5, "fadeOutMs": 50}]}
    plan_path = source / "sound-plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    sound.add_plan(workspace, job, "en", plan_path)
    _timeline(workspace, job, "en", False)
    if _audio_preview(workspace, job, "en"):
        raise RuntimeError("Audio preview failed")
    mix = workspace.resolve_path(workspace.latest_artifact(job, K.AUDIO_MIX, "en"))
    quiet = magnitude(mix, 1.8, 440)
    speech = magnitude(mix, .8, 440)
    duck_db = 20 * math.log10(speech / quiet)
    if not -11 < duck_db < -9:
        raise AssertionError(f"Expected -10dB music duck, measured {duck_db}")
    if magnitude(mix, 2.55, 880) < 100 or magnitude(mix, 1.8, 880) > 20:
        raise AssertionError("SFX did not appear at its anchored time")
    if _remotion(workspace, job, "en", "preview"):
        raise RuntimeError("Video preview failed")
    report = workflow.make_qa(workspace, job, "en")
    if _remotion(workspace, job, "en", "render"):
        raise RuntimeError("Video export failed")
    result = {"jobId": job, "duckDbMeasured": duck_db, "mix": str(mix),
              "qa": report["path"], "export": workspace.latest_artifact(job, K.RENDER, "en")["path"],
              "paidRequests": 0, "audioListening": "not-run", "soundDesign": "not-run"}
    (source / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
