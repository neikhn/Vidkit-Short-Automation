import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from vidkit import library
from vidkit.cli import _add_script, _add_storyboard, _timeline, build_parser
from vidkit.models import ArtifactKind as K, ArtifactStatus as S, Mode
from vidkit.script_bundle import validate_script_bundle
from vidkit.storage import Workspace
from vidkit.timeline import compile_storyboard, validate_storyboard_shape
from vidkit.workflow import add_brief


ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT = {"understanding": "Join the channel", "object": "Three controls",
               "action": "Cursor clicks Like, Subscribe and bell", "result": "All controls active",
               "connection": "End the video"}


def script(language):
    if language == "vi":
        spoken = ("Nếu cách giải thích này hữu ích, hãy theo dõi Hãy Cùng Bắt Đầu AI "
                  "và tương tác cùng kênh để chọn chủ đề tiếp theo.")
        follow, interaction = "theo dõi Hãy Cùng Bắt Đầu AI", "tương tác cùng kênh"
    else:
        spoken = ("If this made embeddings clearer, follow AI Lens and join the conversation "
                  "for deeper examples next week.")
        follow, interaction = "follow AI Lens", "join the conversation"
    return {"editorial_text": spoken, "expected_spoken_text": spoken, "tts_input": spoken,
            "cta": {"spokenText": spoken, "followPhrase": follow,
                    "interactionPhrase": interaction}}


class EngagementCtaTests(unittest.TestCase):
    def test_new_default_and_spoken_engagement_without_button_words(self):
        self.assertEqual(build_parser().parse_args(["create", "Topic"]).workflow_version, 10)
        for language in ("vi", "en"):
            bundle = script(language)
            self.assertEqual(validate_script_bundle(bundle, engagement_cta_language=language), [])
            bundle["tts_input"] = "[warm] " + bundle["tts_input"]
            self.assertEqual(validate_script_bundle(bundle, engagement_cta_language=language), [])
            bundle["cta"]["interactionPhrase"] = "not in the narration"
            self.assertIn("must appear", " ".join(validate_script_bundle(
                bundle, engagement_cta_language=language)))
            bundle = script(language)
            bundle["cta"]["spokenText"] = "Follow the channel and engage."
            self.assertIn("full channel name", " ".join(validate_script_bundle(
                bundle, engagement_cta_language=language)))

    def test_strip_fixtures_and_legacy_component_are_separate(self):
        catalog = ROOT / "renderer/library"
        manifest = json.loads((catalog / "manifest.json").read_text(encoding="utf-8"))
        ids = {item["id"] for item in manifest["components"]}
        self.assertTrue({"cta-end-card", "channel-cta", "channel-cta-strip"} <= ids)
        for language, display in (("vi", "HCDB AI"), ("en", "AI Lens")):
            fixture = json.loads((catalog / "fixtures" / f"channel-cta-strip-{language}.json")
                                 .read_text(encoding="utf-8"))
            self.assertEqual(fixture["scenes"][-1]["componentId"], "channel-cta-strip")
            self.assertEqual(fixture["scenes"][-1]["componentProps"]["channelLabel"], display)
            self.assertGreaterEqual(fixture["durationSeconds"], 5)
            self.assertNotIn("events", fixture["scenes"][-1])

    def test_v9_handoff_uses_scene_duration_for_three_clicks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            job = workspace.create_job("Embedding explainer", ["en"], Mode.AUTOMATIC, workflow_version=9)
            script_source = root / "script.json"
            script_source.write_text(json.dumps(script("en")), encoding="utf-8")
            _add_script(workspace, job, "en", script_source)
            brief = {"angle": "Explain embeddings", "theme": "light-editorial",
                     "backgroundId": "light-editorial-loop", "hook": "How it works",
                     "visualStrategy": "Explain one idea", "beats": [{"id": "one",
                     "development": DEVELOPMENT, "approach": "custom"}],
                     "explanationAlternatives": ["diagram", "example"], "chosenExplanation": "example",
                     "conceptPreview": {"scenes": [
                         *[{"id": role, "role": role, "component": "takeaway", "title": role,
                            "startMs": index * 1000, "endMs": (index + 1) * 1000}
                           for index, role in enumerate(("hook", "evidence", "takeaway"))],
                         {"id": "cta", "role": "cta", "component": "channel-cta-strip",
                          "title": "More examples ahead", "startMs": 3000, "endMs": 9000}]}}
            brief_source = root / "brief.json"
            brief_source.write_text(json.dumps(brief), encoding="utf-8")
            with patch("vidkit.library.entries", return_value=[
                    {"kind": "theme", "id": "light-editorial"},
                    {"kind": "background", "id": "light-editorial-loop", "status": "approved"}]):
                add_brief(workspace, job, "en", brief_source)
            workspace.add_json_artifact(job, None, K.SOURCE, {"claims": []}, S.CHECKED)
            audio = root / "fixture.wav"
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b"\0\0" * 48000)
            workspace.add_file_artifact(job, "en", K.AUDIO, audio, S.CHECKED)
            tokens = script("en")["expected_spoken_text"].rstrip(".").split()
            words = [{"text": token, "start": index * .32, "end": (index + 1) * .32}
                     for index, token in enumerate(tokens)]
            workspace.add_json_artifact(job, "en", K.TRANSCRIPT,
                                        {"words": words, "durationSeconds": 6}, S.CHECKED,
                                        metadata={"variant": "normalized"})
            storyboard = {"schemaVersion": 4, "language": "en", "theme": "light-editorial",
                          "backgroundId": "light-editorial-loop", "scenes": [{"id": "cta", "role": "cta",
                          "layout": "custom", "component": "channel-cta-strip", "title": "More examples ahead",
                          "development": DEVELOPMENT, "startAnchor": {"wordIndex": 0},
                          "endAnchor": {"wordIndex": len(words) - 1}}]}
            self.assertEqual(validate_storyboard_shape(storyboard, require_cta=True,
                             require_background=True, require_engagement_cta=True), [])
            timeline, missing = compile_storyboard({"words": words, "durationSeconds": 6}, storyboard,
                                                   {"assets": []}, "Embedding explainer", "en", "fixture.wav",
                                                   library_entries=library.entries(Workspace(ROOT)),
                                                   require_cta=True, require_background=True,
                                                   channel_cta=script("en")["cta"], engagement_cta=True)
            self.assertEqual(missing, [])
            self.assertEqual(timeline["scenes"][-1]["events"], [])
            self.assertEqual(timeline["scenes"][-1]["componentProps"]["channelLabel"], "AI Lens")
            source = root / "storyboard.json"
            source.write_text(json.dumps(storyboard), encoding="utf-8")
            _add_storyboard(workspace, job, "en", source)
            with patch("vidkit.cli.library.entries", return_value=library.entries(Workspace(ROOT))), \
                    patch("vidkit.cli.checkpoints.current_renderer_lock", return_value={"fixture": "hash"}), \
                    patch("vidkit.cli.sha256_file", return_value="hash"):
                _timeline(workspace, job, "en", False)
            stored = workspace.latest_artifact(job, K.TIMELINE, "en")
            self.assertEqual(stored["status"], S.CHECKED.value)
            self.assertEqual(json.loads(workspace.resolve_path(stored).read_text(encoding="utf-8"))
                             ["scenes"][-1]["componentId"], "channel-cta-strip")
            shorter = json.loads(json.dumps(storyboard))
            short_words = [{"text": token, "start": index * .23, "end": (index + 1) * .23}
                           for index, token in enumerate(tokens)]
            with self.assertRaisesRegex(ValueError, "at least 5 seconds"):
                compile_storyboard({"words": short_words, "durationSeconds": 4.8}, shorter,
                                   {"assets": []}, "Embedding explainer", "en", "fixture.wav",
                                   channel_cta=script("en")["cta"], engagement_cta=True)


if __name__ == "__main__":
    unittest.main()
