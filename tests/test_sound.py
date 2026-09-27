import json
import tempfile
import unittest
import wave
from array import array
from pathlib import Path
from unittest.mock import patch

from vidkit import sound
from vidkit.elevenlabs import ElevenLabsClient
from vidkit.models import ArtifactKind as K, ArtifactStatus as S, Mode
from vidkit.render import prepare_renderer_job
from vidkit.storage import Workspace, sha256_file


def wav(path: Path, seconds: float = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\0\0" * round(24000 * seconds))
    return path


class SoundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = Workspace(self.root)
        self.job = self.workspace.create_job("Sound test", ["en", "vi"], mode=Mode.AUTOMATIC)
        self.words = [{"text": "First", "start": .5, "end": .8},
                      {"text": "next", "start": 1, "end": 1.4}]

    def plan(self, data):
        path = self.root / "plan.json"
        path.write_text(json.dumps({"schemaVersion": 1, **data}), encoding="utf-8")
        return sound.add_plan(self.workspace, self.job, "en", path)

    def asset(self, asset_id, kind, duration=1):
        return sound.register_asset(self.workspace, self.job, wav(self.root / (asset_id + ".wrong"), duration),
            asset_id, kind, {"description": "Fixture", "source": "local fixture", "usageBasis": "generated test signal"})

    def timeline(self):
        return {"durationSeconds": 4, "captions": [], "scenes": [{"id": "main", "events": [
            {"id": "reveal", "atMs": 1600}]}], "sfx": [{"type": "whoosh", "atMs": 0}]}

    def test_format_detection_and_deduplication(self):
        a = self.asset("one", "sfx")
        b = self.asset("two", "sfx")
        self.assertEqual(a["path"], b["path"])
        self.assertTrue(a["path"].endswith(".wav"))
        self.assertEqual(a["mime"], "audio/wav")
        broken = self.root / "broken.mp3"
        broken.write_bytes(b"not audio")
        with self.assertRaises(ValueError):
            sound.inspect_audio(broken)

    def test_impact_alignment_event_order_and_source_trim(self):
        self.asset("ping", "sfx", 1)
        self.plan({"sfx": [{"id": "ping", "purpose": "Reveal result", "assetId": "ping",
            "sceneId": "main", "eventId": "reveal", "trimStartMs": 100, "impactMs": 300,
            "durationMs": 600, "gainDb": -12}]})
        timeline = self.timeline()
        sound.compile_sound(self.workspace, self.job, "en", timeline, self.words)
        track = timeline["soundTracks"][0]
        self.assertEqual(track["startMs"], 1400)
        self.assertEqual(track["endMs"], 2000)
        self.assertEqual(track["trimStartMs"], 100)
        self.assertEqual(timeline["sfx"], [])
        self.assertTrue(sound.locks_match(self.workspace, self.job, "en", timeline))

    def test_word_anchor_and_missing_event_fail(self):
        self.asset("ping", "sfx")
        self.plan({"sfx": [{"id": "ping", "purpose": "Mark word", "assetId": "ping", "wordIndex": 1}]})
        timeline = self.timeline()
        sound.compile_sound(self.workspace, self.job, "en", timeline, self.words)
        self.assertEqual(timeline["soundTracks"][0]["startMs"], 1000)
        self.plan({"sfx": [{"id": "ping", "purpose": "Mark motion", "assetId": "ping",
                            "sceneId": "main", "eventId": "unknown"}]})
        with self.assertRaisesRegex(ValueError, "missing motion"):
            sound.compile_sound(self.workspace, self.job, "en", self.timeline(), self.words)

    def test_music_crossfade_and_speech_ducking(self):
        self.asset("bed", "music", 2)
        self.plan({"music": {"id": "bed", "assetId": "bed", "purpose": "Support explanation",
                             "loop": True, "crossfadeMs": 250, "gainDb": -22}})
        timeline = self.timeline()
        sound.compile_sound(self.workspace, self.job, "en", timeline, self.words)
        tracks = timeline["soundTracks"]
        self.assertEqual([t["startMs"] for t in tracks], [0, 1750, 3500])
        self.assertEqual(tracks[-1]["endMs"], 4000)
        envelope = tracks[0]["envelope"]
        self.assertEqual(envelope, [{"atMs": 400, "db": 0}, {"atMs": 500, "db": -10},
                                    {"atMs": 1400, "db": -10}, {"atMs": 1620, "db": 0}])

    def test_invalid_plan_missing_source_and_overflow(self):
        for cue in ({"wordIndex": 0, "eventId": "x", "sceneId": "main"}, {"wordIndex": -1},
                    {"wordIndex": 0, "gainDb": float("nan")}):
            with self.assertRaises(ValueError):
                self.plan({"sfx": [{"id": "ping", "purpose": "Test", "prompt": "ping", **cue}]})
        self.plan({"sfx": [{"id": "ping", "purpose": "Test", "prompt": "ping", "wordIndex": 0}]})
        self.assertEqual(sound.pending_sounds(self.workspace, self.job, "en"), ["ping"])
        with self.assertRaisesRegex(ValueError, "Missing sound"):
            sound.compile_sound(self.workspace, self.job, "en", self.timeline(), self.words)
        self.asset("ping", "sfx")
        self.plan({"sfx": [{"id": "ping", "purpose": "Test", "assetId": "ping", "wordIndex": 0,
                           "offsetMs": 3000}]})
        with self.assertRaisesRegex(ValueError, "exceeds video"):
            sound.compile_sound(self.workspace, self.job, "en", self.timeline(), self.words)

    def test_short_music_requires_intentional_loop(self):
        self.asset("bed", "music", 2)
        self.plan({"music": {"id": "bed", "assetId": "bed", "purpose": "Support explanation"}})
        with self.assertRaisesRegex(ValueError, "shorter than video"):
            sound.compile_sound(self.workspace, self.job, "en", self.timeline(), self.words)

    def test_sound_edits_preserve_narration_and_transcript(self):
        for language in ("en", "vi"):
            self.workspace.add_file_artifact(self.job, language, K.AUDIO, wav(self.root / "voice.wav", 4), S.CHECKED)
            self.workspace.add_json_artifact(self.job, language, K.TRANSCRIPT, {"words": self.words}, S.CHECKED)
            for kind in (K.TIMELINE, K.AUDIO_MIX, K.PREVIEW, K.QA_REPORT, K.RENDER):
                self.workspace.add_json_artifact(self.job, language, kind, {}, S.CHECKED)
            self.workspace.add_json_artifact(self.job, language, K.APPROVAL, {}, S.APPROVED, metadata={"stage": "export"})
        self.asset("ping", "sfx")
        for language in ("en", "vi"):
            self.assertIsNotNone(self.workspace.latest_artifact(self.job, K.AUDIO, language))
            self.assertIsNotNone(self.workspace.latest_artifact(self.job, K.TRANSCRIPT, language))
            self.assertIsNone(self.workspace.latest_artifact(self.job, K.TIMELINE, language))
            self.assertIsNone(self.workspace.latest_artifact(self.job, K.AUDIO_MIX, language))
            self.assertIsNone(self.workspace.latest_artifact(self.job, K.APPROVAL, language))
        self.plan({"sfx": []})
        self.workspace.invalidate_downstream(self.job, "en", K.AUDIO)
        self.assertIsNotNone(self.workspace.latest_artifact(self.job, K.SOUND_PLAN, "en"))
        self.assertIsNotNone(self.workspace.latest_artifact(self.job, K.SOUND_ASSETS, None))

    def test_renderer_copies_and_checks_sound_content(self):
        asset = self.asset("ping", "sfx")
        self.plan({"sfx": [{"id": "ping", "purpose": "Test", "assetId": "ping", "wordIndex": 0}]})
        timeline = self.timeline()
        sound.compile_sound(self.workspace, self.job, "en", timeline, self.words)
        props = prepare_renderer_job(self.workspace, self.job, "en", timeline, wav(self.root / "voice.wav", 4))
        data = json.loads(props.read_text())
        target = self.root / "renderer/public" / data["soundTracks"][0]["src"]
        self.assertEqual(sha256_file(target), asset["sha256"])
        self.workspace.resolve_path(asset["path"]).write_bytes(b"tampered")
        self.assertFalse(sound.locks_match(self.workspace, self.job, "en", timeline))
        with self.assertRaises(RuntimeError):
            prepare_renderer_job(self.workspace, self.job, "en", timeline, None)

    def test_generation_reuses_take_and_recover_is_idempotent(self):
        self.plan({"sfx": [{"id": "ping", "purpose": "Test", "prompt": "soft ping", "wordIndex": 0}]})
        with patch("vidkit.sound.ElevenLabsClient") as client:
            client.return_value.sound_effect.side_effect = lambda _text, output, **_kwargs: wav(output)
            first = sound.generate(self.workspace, self.job, "en", "sfx", "ping")
            second = sound.generate(self.workspace, self.job, "en", "sfx", "ping")
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(client.return_value.sound_effect.call_count, 1)
            sound.generate(self.workspace, self.job, "en", "sfx", "ping", new_take=True)
            self.assertEqual(client.return_value.sound_effect.call_count, 2)
        requests = list((self.workspace.job_dir(self.job, "en") / "audio/sound-plan/requests").glob("*.json"))
        record = json.loads(requests[0].read_text())
        recovered = sound.recover_request(self.workspace, self.job, "en", record["id"],
                                           self.workspace.resolve_path(record["output"]))
        self.assertEqual(recovered["sha256"], record["sha256"])

    def test_uncertain_request_never_retries_automatically(self):
        self.plan({"music": {"id": "bed", "purpose": "Test", "prompt": "calm underscore", "lengthMs": 4000}})
        with patch("vidkit.sound.ElevenLabsClient") as client:
            client.return_value.compose_music.side_effect = TimeoutError("unknown result")
            with self.assertRaises(TimeoutError):
                sound.generate(self.workspace, self.job, "en", "music")
            with self.assertRaisesRegex(ValueError, "unresolved"):
                sound.generate(self.workspace, self.job, "en", "music", new_take=True)
            self.assertEqual(client.return_value.compose_music.call_count, 1)
            self.assertEqual(client.return_value.compose_music.call_args.kwargs["model_id"], "music_v2_5")

    def test_returning_to_an_earlier_prompt_reuses_persisted_content(self):
        with patch("vidkit.sound.ElevenLabsClient") as client:
            client.return_value.sound_effect.side_effect = lambda text, output, **kwargs: wav(output, 1 if text == "ping" else 2)
            self.plan({"sfx": [{"id": "effect", "purpose": "Test", "prompt": "ping", "wordIndex": 0}]})
            first = sound.generate(self.workspace, self.job, "en", "sfx", "effect")
            self.plan({"sfx": [{"id": "effect", "purpose": "Test", "prompt": "tap", "wordIndex": 0}]})
            second = sound.generate(self.workspace, self.job, "en", "sfx", "effect")
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.plan({"sfx": [{"id": "effect", "purpose": "Test", "prompt": "ping", "wordIndex": 0}]})
            restored = sound.generate(self.workspace, self.job, "en", "sfx", "effect")
            self.assertEqual(restored["sha256"], first["sha256"])
            self.assertEqual(client.return_value.sound_effect.call_count, 2)

    def test_api_payloads_use_separate_endpoints_and_instrumental_music(self):
        client = ElevenLabsClient(api_key="test-key")
        with patch.object(client, "_request", return_value=b"audio") as request:
            client.sound_effect("ping", self.root / "sfx.mp3", duration_seconds=.5)
            call = request.call_args
            self.assertTrue(call.args[0].startswith("/v1/sound-generation?"))
            self.assertEqual(json.loads(call.args[1])["model_id"], "eleven_text_to_sound_v2")
            client.compose_music("bed", self.root / "music.mp3", music_length_ms=4000)
            self.assertTrue(request.call_args.args[0].startswith("/v1/music?"))
            self.assertTrue(json.loads(request.call_args.args[1])["force_instrumental"])
            self.assertEqual(json.loads(request.call_args.args[1])["model_id"], "music_v2_5")
            client.compose_music("bed", self.root / "music.mp3", music_length_ms=4000, model_id="music_v2")
            self.assertEqual(json.loads(request.call_args.args[1])["model_id"], "music_v2")
            count = request.call_count
            with self.assertRaises(ValueError):
                client.compose_music("bed", self.root / "music.mp3", music_length_ms=2000)
            self.assertEqual(request.call_count, count)

    def test_shared_audio_deduplicates_and_rebuilds_index(self):
        from vidkit import library
        a = self.asset("ping", "sfx")
        shared = sound.share_asset(self.workspace, self.job, "ping", "Use for small UI confirmations")
        other = self.workspace.create_job("Another video", ["en"])
        with patch("vidkit.library._builtins", return_value=[]):
            matches = library.search(self.workspace, "sfx", kind="asset")
            self.assertEqual(len(matches), 1)
            reused = sound.reuse_asset(self.workspace, other, shared["id"], "confirmation")
        self.assertEqual(reused["sha256"], a["sha256"])
        with self.workspace.connect() as conn:
            conn.execute("DELETE FROM audio_library")
        self.assertEqual(sound.reindex_library(self.workspace), 1)
        self.assertEqual(sound.share_asset(self.workspace, self.job, "ping", "UI sounds")["id"], shared["id"])

    def test_review_gate_blocks_paid_calls(self):
        review_job = self.workspace.create_job("Review", ["en"])
        with patch("vidkit.sound.ElevenLabsClient") as client:
            with self.assertRaisesRegex(ValueError, "Concept approval"):
                sound.generate(self.workspace, review_job, "en", "music")
            client.assert_not_called()

    def test_level_measurement_checks_decoded_samples_without_claiming_listening(self):
        source = self.root / "mixed.mp4"
        source.write_bytes(b"decoder fixture")
        samples = [0.0, .5, -.8]
        def decode(command, **kwargs):
            self.assertIn("pcm_s16le", command)
            with wave.open(str(command[-1]), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
                output.writeframes(array("h", [max(-32768, min(32767, round(value * 32768))) for value in samples]).tobytes())
        with patch("vidkit.sound.shutil.which", return_value="ffmpeg"), \
                patch("vidkit.sound.subprocess.run", side_effect=decode):
            report = sound.audio_level_check(self.workspace, source)
            self.assertEqual(report["status"], "pass")
            self.assertIn("not true-peak", report["evidence"][1])
            samples[:] = [0.0, 1.0, -1.0]
            self.assertEqual(sound.audio_level_check(self.workspace, source)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
