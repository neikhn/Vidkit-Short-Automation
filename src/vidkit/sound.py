from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import uuid
import wave
import subprocess
import tempfile
import sys
from array import array
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile, MutagenError

from .elevenlabs import ElevenLabsClient
from .models import ArtifactKind as K, ArtifactStatus as S
from .storage import Workspace, sha256_file, utc_now


ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def number(data: dict[str, Any], key: str, default: float, minimum: float, maximum: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{key} must be a finite number between {minimum} and {maximum}")
    return float(value)


def inspect_audio(source: Path) -> dict[str, Any]:
    try:
        with wave.open(str(source), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
            result = {"extension": ".wav", "mime": "audio/wav", "durationMs": round(duration * 1000),
                      "sampleRate": audio.getframerate(), "channels": audio.getnchannels()}
    except (wave.Error, EOFError):
        try:
            media = MutagenFile(source)
            if media is None or media.__class__.__name__ != "MP3":
                raise ValueError("Sound assets must be readable WAV or MP3 files")
            result = {"extension": ".mp3", "mime": "audio/mpeg", "durationMs": round(media.info.length * 1000),
                      "sampleRate": media.info.sample_rate, "channels": media.info.channels}
        except (MutagenError, AttributeError) as exc:
            raise ValueError("Unreadable audio asset") from exc
    if result["durationMs"] <= 0:
        raise ValueError("Audio asset is empty")
    return result


def load_assets(workspace: Workspace, job_id: str) -> dict[str, Any]:
    artifact = workspace.latest_artifact(job_id, K.SOUND_ASSETS, None)
    return json.loads(workspace.resolve_path(artifact).read_text(encoding="utf-8")) if artifact else {"assets": []}


def register_asset(workspace: Workspace, job_id: str, source: Path, asset_id: str, kind: str,
                   provenance: dict[str, Any]) -> dict[str, Any]:
    if not ID.fullmatch(asset_id) or kind not in {"sfx", "music"}:
        raise ValueError("Sound asset needs lowercase hyphenated id and sfx/music kind")
    if not provenance.get("description") or not provenance.get("usageBasis") or not provenance.get("source"):
        raise ValueError("Sound asset needs description, source and usageBasis")
    info = inspect_audio(source)
    checksum = sha256_file(source)
    destination = workspace.job_root(job_id) / "audio-assets" / kind / (checksum + info["extension"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha256_file(destination) != checksum:
        raise ValueError("Audio cache checksum mismatch")
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    entry = {**provenance, **info, "id": asset_id, "kind": kind,
             "originalName": provenance.get("originalName", source.name),
             "path": destination.relative_to(workspace.workspace_root).as_posix(), "sha256": checksum,
             "retrievedAt": utc_now()}
    manifest = load_assets(workspace, job_id)
    manifest["assets"] = [item for item in manifest["assets"] if item["id"] != asset_id] + [entry]
    workspace.add_json_artifact(job_id, None, K.SOUND_ASSETS, manifest, S.CHECKED)
    for language in workspace.get_job(job_id)["languages"]:
        workspace.invalidate_downstream(job_id, language, K.SOUND_ASSETS)
    return entry


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("schemaVersion") != 1 or not isinstance(plan.get("sfx", []), list):
        raise ValueError("Sound plan needs schemaVersion 1 and sfx list")
    cues = plan.get("sfx", [])
    music = plan.get("music")
    if music is not None and not isinstance(music, dict):
        raise ValueError("music must be an object or null")
    ids = []
    for item in [*cues, *([music] if music else [])]:
        if not isinstance(item, dict) or not ID.fullmatch(str(item.get("id", ""))):
            raise ValueError("Every sound needs a lowercase hyphenated id")
        ids.append(item["id"])
        if not item.get("purpose") or (not item.get("assetId") and not item.get("prompt")):
            raise ValueError("Every sound needs purpose and assetId or generation prompt")
        number(item, "gainDb", -22 if item is music else -16, -80, 0)
        for key in ("trimStartMs", "fadeInMs", "fadeOutMs", "impactMs", "crossfadeMs"):
            number(item, key, 0, 0, 600000)
        number(item, "offsetMs", 0, -600000, 600000)
        for key in ("loop", "forceInstrumental"):
            if key in item and not isinstance(item[key], bool):
                raise ValueError(f"{key} must be boolean")
        if item.get("assetId") and not ID.fullmatch(str(item["assetId"])):
            raise ValueError("Invalid sound assetId")
    if len(ids) != len(set(ids)):
        raise ValueError("Sound ids must be unique")
    for cue in cues:
        if ("wordIndex" in cue) == ("eventId" in cue):
            raise ValueError("SFX needs exactly one wordIndex or eventId anchor")
        if "wordIndex" in cue and (type(cue["wordIndex"]) is not int or cue["wordIndex"] < 0):
            raise ValueError("wordIndex must be nonnegative integer")
        if "eventId" in cue and not cue.get("sceneId"):
            raise ValueError("Motion SFX needs sceneId and eventId")
        number(cue, "durationSeconds", 1, 0.5, 30)
        number(cue, "promptInfluence", .3, 0, 1)
        if "durationMs" in cue:
            number(cue, "durationMs", 1, 1, 30000)
    if music:
        if len(str(music.get("prompt", ""))) > 4100:
            raise ValueError("Music prompt exceeds 4100 characters")
        if "lengthMs" in music:
            length = number(music, "lengthMs", 3000, 3000, 600000)
            if length != int(length):
                raise ValueError("lengthMs must be an integer")
        number(music, "duckDb", -10, -40, 0)
    for item in [*cues, *([music] if music else [])]:
        if "prompt" in item and (not isinstance(item["prompt"], str) or not item["prompt"].strip()):
            raise ValueError("Generation prompt must be nonempty text")


def add_plan(workspace: Workspace, job_id: str, language: str, source: Path) -> dict[str, Any]:
    if language not in workspace.get_job(job_id)["languages"]:
        raise ValueError("Unknown job language")
    plan = json.loads(source.read_text(encoding="utf-8"))
    validate_plan(plan)
    workspace.invalidate_downstream(job_id, language, K.SOUND_PLAN)
    return workspace.add_json_artifact(job_id, language, K.SOUND_PLAN, plan, S.CHECKED)


def get_plan(workspace: Workspace, job_id: str, language: str) -> dict[str, Any]:
    artifact = workspace.latest_artifact(job_id, K.SOUND_PLAN, language)
    if not artifact:
        raise ValueError("Add a sound plan first")
    if sha256_file(workspace.resolve_path(artifact)) != artifact["sha256"]:
        raise ValueError("Sound plan checksum mismatch; import your edit with add-sound-plan")
    return json.loads(workspace.resolve_path(artifact).read_text(encoding="utf-8"))


def generate(workspace: Workspace, job_id: str, language: str, kind: str,
             cue_id: str | None = None, new_take: bool = False) -> dict[str, Any]:
    from .media import audio_duration
    from .workflow import current_approval
    job = workspace.get_job(job_id)
    if job["mode"] == "review" and not current_approval(workspace, job_id, language, "concept"):
        raise ValueError("Concept approval is required before sound generation")
    plan = get_plan(workspace, job_id, language)
    validate_plan(plan)
    spec = plan.get("music") if kind == "music" else next(
        (cue for cue in plan.get("sfx", []) if cue["id"] == cue_id), None)
    if not spec or not spec.get("prompt"):
        raise ValueError("Selected sound needs a generation prompt")
    if kind == "music":
        narration = workspace.latest_artifact(job_id, K.AUDIO, language)
        if "lengthMs" not in spec and not narration:
            raise ValueError("Music needs narration or explicit lengthMs")
        duration = audio_duration(workspace.resolve_path(narration)) if narration else None
        length = spec.get("lengthMs", max(3000, math.ceil((duration or 0) * 1000)))
        if duration is None and "lengthMs" not in spec:
            raise ValueError("Cannot measure narration duration")
        number({"lengthMs": length}, "lengthMs", 3000, 3000, 600000)
        settings = {"model_id": spec.get("modelId", "music_v2_5"), "music_length_ms": length,
                    "force_instrumental": spec.get("forceInstrumental", True)}
    else:
        settings = {"model_id": spec.get("modelId", "eleven_text_to_sound_v2"),
                    "duration_seconds": spec.get("durationSeconds", 1),
                    "prompt_influence": spec.get("promptInfluence", .3), "loop": spec.get("loop", False)}
    key = hashlib.sha256(json.dumps({"kind": kind, "prompt": spec["prompt"], "settings": settings},
                                   sort_keys=True).encode()).hexdigest()
    assets = load_assets(workspace, job_id)["assets"]
    existing = next((item for item in assets if item.get("generationKey") == key), None)
    if existing and not new_take:
        if sha256_file(workspace.resolve_path(existing["path"])) != existing["sha256"]:
            raise ValueError("Reusable audio checksum mismatch")
        # Bind the same content to this cue id, even when another cue originally generated it.
        if existing["id"] == spec.get("assetId", spec["id"]):
            return existing
        return register_asset(workspace, job_id, workspace.resolve_path(existing["path"]),
                              spec.get("assetId", spec["id"]), kind, existing)
    request_dir = workspace.job_dir(job_id, language) / "audio" / "sound-plan" / "requests"
    request_dir.mkdir(parents=True, exist_ok=True)
    previous = [json.loads(path.read_text(encoding="utf-8")) for path in request_dir.glob("*.json")]
    if not new_take:
        completed = next((item for item in reversed(previous)
                          if item.get("generationKey") == key and item["state"] == "completed"), None)
        if completed:
            cached = workspace.resolve_path(completed.get("assetPath", completed["output"]))
            if cached.is_file() and sha256_file(cached) == completed["sha256"]:
                reused = recover_request(workspace, job_id, language, completed["id"], cached)
                if reused["id"] != spec.get("assetId", spec["id"]):
                    return register_asset(workspace, job_id, cached, spec.get("assetId", spec["id"]), kind,
                                          {**reused, "description": spec["purpose"]})
                return reused
    if any(item.get("generationKey") == key and item["state"] != "completed" for item in previous):
        raise ValueError("Previous request is unresolved; inspect audio requests and recover its file before retrying")
    client = ElevenLabsClient()  # Validate credentials before recording an attempted paid request.
    request_id = key if not new_take else key + "-" + uuid.uuid4().hex[:8]
    record_path = request_dir / (request_id + ".json")
    output = request_dir / (request_id + ".mp3")
    record = {"id": request_id, "generationKey": key, "kind": kind, "prompt": spec["prompt"],
              "settings": settings, "assetId": spec.get("assetId", spec["id"]),
              "description": spec["purpose"], "state": "pending", "createdAt": utc_now(),
              "output": output.relative_to(workspace.workspace_root).as_posix()}
    # Exclusive creation prevents duplicate identical calls from concurrent agents.
    with record_path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    try:
        if kind == "music":
            client.compose_music(spec["prompt"], output, **settings)
        else:
            client.sound_effect(spec["prompt"], output, **settings)
        return recover_request(workspace, job_id, language, request_id, output)
    except Exception:
        record["state"] = "unresolved"
        _write_record(record_path, record)
        raise


def _write_record(path: Path, record: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def recover_request(workspace: Workspace, job_id: str, language: str, request_id: str, source: Path) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}(?:-[a-f0-9]{8})?", request_id):
        raise ValueError("Invalid request id")
    path = workspace.job_dir(job_id, language) / "audio" / "sound-plan" / "requests" / (request_id + ".json")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["state"] == "completed":
        if sha256_file(source) != record["sha256"]:
            raise ValueError("Completed request cannot be recovered with different content")
        existing = next((a for a in load_assets(workspace, job_id)["assets"]
                         if a["id"] == record["assetId"] and a["sha256"] == record["sha256"]), None)
        if existing:
            return existing
    entry = register_asset(workspace, job_id, source, record["assetId"], record["kind"], {
        "description": record["description"], "source": "ElevenLabs API", "usageBasis": "ElevenLabs account terms; verify for publication",
        "provider": "elevenlabs", "prompt": record["prompt"], "settings": record["settings"],
        "generationKey": record["generationKey"], "requestId": request_id})
    record.update(state="completed", sha256=entry["sha256"], assetPath=entry["path"], completedAt=utc_now())
    _write_record(path, record)
    return entry


def pending_sounds(workspace: Workspace, job_id: str, language: str) -> list[str]:
    artifact = workspace.latest_artifact(job_id, K.SOUND_PLAN, language)
    if not artifact:
        return []
    plan = get_plan(workspace, job_id, language)
    assets = {item["id"]: item for item in load_assets(workspace, job_id)["assets"]}
    pending = []
    api_fields = {"modelId": "model_id", "lengthMs": "music_length_ms", "durationSeconds": "duration_seconds",
                  "promptInfluence": "prompt_influence", "forceInstrumental": "force_instrumental", "loop": "loop"}
    for item in [*plan.get("sfx", []), *([plan["music"]] if plan.get("music") else [])]:
        asset_id = item.get("assetId", item["id"])
        asset = assets.get(asset_id)
        if not asset:
            pending.append(asset_id)
        elif not item.get("assetId") and item.get("prompt") and asset.get("provider") == "elevenlabs":
            generation_fields = {"modelId", "lengthMs", "forceInstrumental"} if asset["kind"] == "music" else {
                "modelId", "durationSeconds", "promptInfluence", "loop"}
            changed = asset.get("prompt") != item["prompt"] or any(
                asset.get("settings", {}).get(api_key) != item[key]
                for key, api_key in api_fields.items() if key in item and key in generation_fields)
            if changed:
                pending.append(asset_id)
    return pending


def compile_sound(workspace: Workspace, job_id: str, language: str,
                  timeline: dict[str, Any], words: list[dict[str, Any]]) -> None:
    artifact = workspace.latest_artifact(job_id, K.SOUND_PLAN, language)
    if not artifact:
        return  # Existing jobs retain their legacy whoosh path.
    plan = get_plan(workspace, job_id, language)
    validate_plan(plan)
    assets = {item["id"]: item for item in load_assets(workspace, job_id)["assets"]}
    missing = pending_sounds(workspace, job_id, language)
    if missing:
        raise ValueError("Missing sound assets: " + ", ".join(missing))
    duration = round(timeline["durationSeconds"] * 1000)
    tracks = []
    for spec in [*plan.get("sfx", []), *([plan["music"]] if plan.get("music") else [])]:
        is_music = spec is plan.get("music")
        asset = assets[spec.get("assetId", spec["id"])]
        if asset["kind"] != ("music" if is_music else "sfx"):
            raise ValueError("Sound asset kind does not match cue")
        if sha256_file(workspace.resolve_path(asset["path"])) != asset["sha256"]:
            raise ValueError(f"Sound checksum mismatch: {asset['id']}")
        if is_music:
            anchor = 0
        elif "wordIndex" in spec:
            index = spec["wordIndex"]
            if index >= len(words):
                raise ValueError("SFX word anchor is outside transcript")
            anchor = round(float(words[index]["start"]) * 1000)
        else:
            scene = next((s for s in timeline["scenes"] if s["id"] == spec["sceneId"]), None)
            event = next((e for e in (scene or {}).get("events", []) if e["id"] == spec["eventId"]), None)
            if not event:
                raise ValueError("SFX refers to missing motion event")
            anchor = event["atMs"]
        trim = spec.get("trimStartMs", 0)
        available = asset["durationMs"] - trim
        if available <= 0:
            raise ValueError("Sound trim exceeds source duration")
        impact = spec.get("impactMs", trim)
        if not trim <= impact < asset["durationMs"]:
            raise ValueError("SFX impact must be inside selected source")
        start = anchor + spec.get("offsetMs", 0) - (0 if is_music else impact - trim)
        if start < 0 or start >= duration:
            raise ValueError(f"Sound cue {spec['id']} starts outside video")
        target_length = duration - start if is_music else spec.get("durationMs", available)
        if target_length > available and not (is_music and spec.get("loop", False)):
            if is_music:
                raise ValueError("Music is shorter than video; choose a verified loop or longer asset")
            raise ValueError("SFX duration exceeds source")
        if start + target_length > duration + 1:
            raise ValueError("Sound cue exceeds video; trim it explicitly")
        fade_in = spec.get("fadeInMs", 600 if is_music else 15)
        fade_out = spec.get("fadeOutMs", 800 if is_music else 40)
        crossfade = spec.get("crossfadeMs", 250 if is_music else 0) if spec.get("loop") else 0
        if is_music and spec.get("loop") and available < 500:
            raise ValueError("Music loop source must be at least 500ms")
        if crossfade >= available / 2:
            raise ValueError("Loop crossfade must be shorter than half the selected source")
        envelope = speech_envelope(words, spec.get("duckDb", -10)) if is_music else []
        position = start
        end = start + target_length
        while position < end:
            length = min(available, end - position)
            incoming = fade_in if position == start else crossfade
            outgoing = fade_out if position + length >= end else crossfade
            if "fadeOutMs" not in spec and position + length >= end:
                outgoing = min(outgoing, max(0, length - incoming))
            if incoming + outgoing > length:
                raise ValueError("Sound fades exceed segment duration")
            tracks.append({"id": f"{spec['id']}-{len(tracks)}", "cueId": spec["id"],
                           "kind": asset["kind"], "asset": asset, "startMs": position,
                           "endMs": position + length, "trimStartMs": trim,
                           "gainDb": spec.get("gainDb", -22 if is_music else -16),
                           "fadeInMs": incoming, "fadeOutMs": outgoing, "envelope": envelope})
            if position + length >= end:
                break
            position += available - crossfade
    timeline["soundTracks"] = tracks
    timeline["sfx"] = []  # Explicit plan replaces legacy hard-coded whooshes.
    timeline["soundPlanLock"] = {"revision": artifact["revision"], "sha256": artifact["sha256"]}


def speech_envelope(words: list[dict[str, Any]], duck_db: float) -> list[dict[str, float]]:
    ranges: list[list[float]] = []
    for word in words:
        start, end = float(word["start"]) * 1000, float(word["end"]) * 1000
        if ranges and start - ranges[-1][1] <= 400:
            ranges[-1][1] = max(end, ranges[-1][1])
        else:
            ranges.append([start, end])
    points = []
    for start, end in ranges:
        points.extend([{"atMs": max(0, start - 100), "db": 0}, {"atMs": start, "db": duck_db},
                       {"atMs": end, "db": duck_db}, {"atMs": end + 220, "db": 0}])
    # At time zero the ducked value wins over its coincident attack start.
    return list({point["atMs"]: point for point in points}.values())


def locks_match(workspace: Workspace, job_id: str, language: str, timeline: dict[str, Any]) -> bool:
    artifact = workspace.latest_artifact(job_id, K.SOUND_PLAN, language)
    lock = timeline.get("soundPlanLock")
    if bool(artifact) != bool(lock):
        return False
    if artifact and (artifact["sha256"] != lock["sha256"] or artifact["revision"] != lock["revision"]
                     or sha256_file(workspace.resolve_path(artifact)) != lock["sha256"]):
        return False
    current = {item["id"]: item for item in load_assets(workspace, job_id)["assets"]}
    for track in timeline.get("soundTracks", []):
        asset = track["asset"]
        if (current.get(asset["id"], {}).get("sha256") != asset["sha256"]
                or not workspace.resolve_path(asset["path"]).is_file()
                or sha256_file(workspace.resolve_path(asset["path"])) != asset["sha256"]):
            return False
    return True


def share_asset(workspace: Workspace, job_id: str, asset_id: str, purpose: str) -> dict[str, Any]:
    if not purpose.strip():
        raise ValueError("Shared audio needs a reuse purpose")
    asset = next((a for a in load_assets(workspace, job_id)["assets"] if a["id"] == asset_id), None)
    if not asset:
        raise ValueError("Unknown sound asset")
    source = workspace.resolve_path(asset["path"])
    if sha256_file(source) != asset["sha256"]:
        raise ValueError("Shared audio checksum mismatch")
    directory = workspace.workspace_root / "library" / "audio" / asset["sha256"]
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / ("audio" + asset["extension"])
    shutil.copy2(source, target)
    item = {**asset, "id": "audio-" + asset["sha256"][:16], "version": "1.0.0", "kind": "asset",
            "soundKind": asset["kind"], "status": "candidate", "evidenceType": "generated-audio" if asset.get("provider") else "imported-audio",
            "tags": ["audio", asset["kind"]], "useCases": [purpose], "limitations": ["Listen and verify usage terms for each publication"],
            "propsSchema": {}, "license": asset["usageBasis"], "preview": "audio",
            "path": target.relative_to(workspace.workspace_root).as_posix()}
    manifest = directory / "manifest.json"
    manifest.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    # Existing library search/show/preview discovers this entry without promoting it into Git.
    candidate = workspace.workspace_root / "library" / "candidates" / (item["id"] + ".json")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    reindex_library(workspace)
    return item


def reindex_library(workspace: Workspace) -> int:
    manifests = []
    for path in (workspace.workspace_root / "library/audio").glob("*/manifest.json"):
        entry = json.loads(path.read_text(encoding="utf-8"))
        if sha256_file(workspace.resolve_path(entry["path"])) != entry["sha256"]:
            raise ValueError("Library audio checksum mismatch")
        manifests.append((entry["sha256"], path.relative_to(workspace.workspace_root).as_posix()))
        candidate = workspace.workspace_root / "library/candidates" / (entry["id"] + ".json")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    with workspace.connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS audio_library (sha256 TEXT PRIMARY KEY, manifest_path TEXT NOT NULL)")
        conn.execute("DELETE FROM audio_library")
        conn.executemany("INSERT INTO audio_library VALUES (?, ?)", manifests)
    return len(manifests)


def reuse_asset(workspace: Workspace, job_id: str, entry_id: str, asset_id: str) -> dict[str, Any]:
    from .library import show
    entry = show(workspace, entry_id)
    if entry.get("soundKind") not in {"sfx", "music"}:
        raise ValueError("Library entry is not an audio asset")
    source = workspace.resolve_path(entry["path"])
    if sha256_file(source) != entry["sha256"]:
        raise ValueError("Library audio checksum mismatch")
    return register_asset(workspace, job_id, source, asset_id, entry["soundKind"],
                          {**entry, "libraryId": entry_id})


def audio_level_check(workspace: Workspace, path: Path) -> dict[str, Any]:
    bundled = workspace.project_root / "renderer/node_modules/@remotion/compositor-win32-x64-msvc/ffmpeg.exe"
    executable = shutil.which("ffmpeg") or (str(bundled) if bundled.is_file() else None)
    if not executable:
        return {"status": "not-run", "evidence": ["ffmpeg unavailable; no listening inferred"]}
    try:
        # Remotion's minimal ffmpeg supports PCM16 WAV, but omits astats and raw float muxing.
        with tempfile.TemporaryDirectory(prefix="vidkit-levels-", dir=workspace.cache_root) as directory:
            pcm = Path(directory) / "decoded.wav"
            subprocess.run([executable, "-hide_banner", "-y", "-i", str(path), "-map", "0:a:0", "-vn",
                            "-f", "wav", "-acodec", "pcm_s16le", str(pcm)],
                           capture_output=True, timeout=60, check=True)
            count, peak, square_sum = 0, 0.0, 0.0
            with wave.open(str(pcm), "rb") as handle:
                if handle.getsampwidth() != 2:
                    raise ValueError("Expected PCM16 audio")
                while block := handle.readframes(16384):
                    samples = array("h")
                    samples.frombytes(block)
                    if sys.byteorder != "little":
                        samples.byteswap()
                    count += len(samples)
                    peak = max(peak, max(abs(value) for value in samples) / 32768)
                    square_sum += sum(value * value for value in samples) / (32768 ** 2)
        if not count:
            raise ValueError("No decoded audio samples")
        peak_db = 20 * math.log10(peak) if peak else -math.inf
        rms_db = 10 * math.log10(square_sum / count) if square_sum else -math.inf
        return {"status": "fail" if peak_db >= -0.1 else "pass",
                "evidence": [f"PCM16 decoded sample peak {peak_db:.2f} dBFS; RMS {rms_db:.2f} dBFS",
                             "Near-full-scale samples fail at -0.1 dBFS; this is not true-peak analysis or listening"]}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, OSError, wave.Error):
        return {"status": "fail", "evidence": ["Could not measure the decoded audio mix"]}
