import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from vidkit import library
from vidkit.channels import CHANNELS
from vidkit.cli import _add_script, _add_storyboard, _concept_preview, _timeline
from vidkit.models import ArtifactKind as K, ArtifactStatus as S, Mode
from vidkit.script_bundle import validate_script_bundle
from vidkit.storage import Workspace
from vidkit.timeline import compile_storyboard, validate_storyboard_shape
from vidkit.workflow import add_brief


ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT = {"understanding": "Know what to do next", "object": "Channel CTA",
               "action": "Click two buttons", "result": "Liked and subscribed", "connection": "End"}


def script(language: str) -> dict:
    if language == "vi":
        spoken = "Nếu hữu ích, hãy nhấn Thích và đăng ký kênh Hãy Cùng Bắt Đầu AI để xem tiếp."
        like, subscribe = "nhấn Thích", "đăng ký kênh Hãy Cùng Bắt Đầu AI"
    else:
        spoken = "If this helped, like the video and subscribe to AI Lens for more clear explainers."
        like, subscribe = "like the video", "subscribe to AI Lens"
    return {"editorial_text": spoken, "expected_spoken_text": spoken, "tts_input": spoken,
            "cta": {"spokenText": spoken, "likePhrase": like, "subscribePhrase": subscribe}}


class ChannelCtaTests(unittest.TestCase):
    def test_script_requires_both_actions_and_spoken_channel_name(self):
        for language in ("vi", "en"):
            bundle = script(language)
            self.assertEqual(validate_script_bundle(bundle, channel_cta_language=language), [])
            bundle["tts_input"] = "[warm] " + bundle["tts_input"]
            self.assertEqual(validate_script_bundle(bundle, channel_cta_language=language), [])
            bundle["cta"]["subscribePhrase"] = "subscribe" if language == "en" else "đăng ký"
            self.assertIn("full channel name", " ".join(validate_script_bundle(
                bundle, channel_cta_language=language)))
            bundle = script(language)
            bundle["cta"]["likePhrase"], bundle["cta"]["subscribePhrase"] = (
                bundle["cta"]["subscribePhrase"], bundle["cta"]["likePhrase"])
            self.assertIn("Like before Subscribe", " ".join(validate_script_bundle(
                bundle, channel_cta_language=language)))
            bundle = script(language)
            bundle["cta"]["likePhrase"] = "hữu ích" if language == "vi" else "this helped"
            self.assertIn("spoken", " ".join(validate_script_bundle(
                bundle, channel_cta_language=language)))
        self.assertEqual(CHANNELS["vi"]["display"], "HCDB AI")
        self.assertEqual(CHANNELS["en"]["spoken"], "AI Lens")

    def test_storyboard_compiles_word_anchored_clicks_and_channel_props(self):
        tokens = "Nếu hữu ích hãy nhấn Thích và đăng ký kênh Hãy Cùng Bắt Đầu AI để xem tiếp".split()
        words = [{"text": token, "start": index * .36, "end": (index + 1) * .36}
                 for index, token in enumerate(tokens)]
        scene = {"id": "cta", "role": "cta", "layout": "custom", "component": "channel-cta",
                 "title": "Hiểu AI rõ hơn", "body": "Video ngắn, có nguồn", "development": DEVELOPMENT,
                 "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": len(words) - 1},
                 "entities": [{"id": "like"}, {"id": "subscribe"}],
                 "events": [{"id": "like-click", "entityId": "like", "wordIndex": 5, "durationFrames": 8},
                            {"id": "subscribe-click", "entityId": "subscribe", "wordIndex": 8,
                             "durationFrames": 8}]}
        storyboard = {"schemaVersion": 4, "language": "vi", "theme": "dark-grid",
                      "backgroundId": "grid-drift", "scenes": [scene]}
        self.assertEqual(validate_storyboard_shape(storyboard, require_cta=True,
                         require_background=True, require_channel_cta=True), [])
        timeline, missing = compile_storyboard({"words": words}, storyboard, {"assets": []},
                                               "Example", "vi", "voice.mp3",
                                               library_entries=library.entries(Workspace(ROOT)),
                                               require_cta=True, center_visuals=True,
                                               require_background=True, channel_cta=script("vi")["cta"])
        self.assertEqual(missing, [])
        compiled = timeline["scenes"][-1]
        self.assertEqual(compiled["componentProps"]["channelLabel"], "HCDB AI")
        self.assertEqual([event["id"] for event in compiled["events"]],
                         ["like-click", "subscribe-click"])
        self.assertLess(compiled["events"][0]["atFrame"], compiled["events"][1]["atFrame"])
        with self.assertRaisesRegex(ValueError, "word anchor must match"):
            altered = json.loads(json.dumps(storyboard))
            altered["scenes"][0]["events"][0]["wordIndex"] = 2
            compile_storyboard({"words": words}, altered, {"assets": []}, "Example", "vi", "voice.mp3",
                               library_entries=library.entries(Workspace(ROOT)), require_cta=True,
                               channel_cta=script("vi")["cta"])

    def test_fixtures_include_both_languages_and_leave_legacy_component(self):
        catalog = ROOT / "renderer/library"
        manifest = json.loads((catalog / "manifest.json").read_text(encoding="utf-8"))
        ids = {entry["id"] for entry in manifest["components"]}
        self.assertIn("cta-end-card", ids)
        self.assertIn("channel-cta", ids)
        for language in ("vi", "en"):
            fixture = json.loads((catalog / "fixtures" / f"channel-cta-{language}.json").read_text(encoding="utf-8"))
            self.assertEqual(fixture["scenes"][-1]["componentId"], "channel-cta")
            self.assertEqual(fixture["scenes"][-1]["componentProps"]["channelLabel"],
                             CHANNELS[language]["display"])
            self.assertGreaterEqual(fixture["durationSeconds"], 4)

    def test_v8_job_handoff_with_local_audio_and_transcript_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            job = workspace.create_job("AI Lens explainer", ["en"], Mode.AUTOMATIC, workflow_version=8)
            source = root / "script.json"
            source.write_text(json.dumps(script("en")), encoding="utf-8")
            _add_script(workspace, job, "en", source)
            brief = {"angle": "Explain the concept", "theme": "dark-grid", "backgroundId": "grid-drift",
                     "hook": "Why it matters", "visualStrategy": "Show one clear example",
                     "beats": [{"id": "one", "development": DEVELOPMENT, "approach": "custom"}],
                     "explanationAlternatives": ["diagram", "example"], "chosenExplanation": "example",
                     "conceptPreview": {"scenes": [
                         *[{"id": role, "role": role, "component": "takeaway", "title": role,
                            "startMs": index * 1000, "endMs": (index + 1) * 1000}
                           for index, role in enumerate(("hook", "evidence", "takeaway"))],
                         {"id": "cta", "role": "cta", "component": "channel-cta", "title": "Learn AI clearly",
                          "startMs": 3000, "endMs": 7800}]}}
            brief_source = root / "brief.json"
            brief_source.write_text(json.dumps(brief), encoding="utf-8")
            with patch("vidkit.library.entries", return_value=[
                    {"kind": "theme", "id": "dark-grid"},
                    {"kind": "background", "id": "grid-drift", "status": "approved"}]):
                add_brief(workspace, job, "en", brief_source)
            workspace.add_json_artifact(job, None, K.SOURCE, {"claims": []}, S.CHECKED)
            audio = root / "fixture.wav"
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b"\0\0" * 40000)
            workspace.add_file_artifact(job, "en", K.AUDIO, audio, S.CHECKED)
            tokens = script("en")["expected_spoken_text"].rstrip(".").split()
            words = [{"text": token, "start": index * .3, "end": (index + 1) * .3}
                     for index, token in enumerate(tokens)]
            workspace.add_json_artifact(job, "en", K.TRANSCRIPT, {"words": words}, S.CHECKED,
                                        metadata={"variant": "normalized"})
            like_index, subscribe_index = tokens.index("like"), tokens.index("subscribe")
            storyboard = {"schemaVersion": 4, "language": "en", "theme": "dark-grid",
                          "backgroundId": "grid-drift", "scenes": [{"id": "cta", "role": "cta",
                          "layout": "custom", "component": "channel-cta", "title": "Learn AI clearly",
                          "development": DEVELOPMENT, "startAnchor": {"wordIndex": 0},
                          "endAnchor": {"wordIndex": len(words) - 1},
                          "entities": [{"id": "like"}, {"id": "subscribe"}],
                          "events": [{"id": "like-click", "entityId": "like", "wordIndex": like_index,
                                      "durationFrames": 8},
                                     {"id": "subscribe-click", "entityId": "subscribe",
                                      "wordIndex": subscribe_index, "durationFrames": 8}]}]}
            self.assertEqual(validate_storyboard_shape(storyboard, require_cta=True,
                             require_background=True, require_channel_cta=True), [])
            timeline, missing = compile_storyboard({"words": words, "durationSeconds": 5}, storyboard,
                                                   {"assets": []}, "AI Lens explainer", "en", "fixture.wav",
                                                   library_entries=library.entries(Workspace(ROOT)),
                                                   require_cta=True, center_visuals=True,
                                                   require_background=True, channel_cta=script("en")["cta"])
            self.assertEqual(missing, [])
            self.assertEqual(timeline["scenes"][-1]["componentProps"]["channelLabel"], "AI Lens")
            self.assertGreater(timeline["scenes"][-1]["events"][1]["atFrame"],
                               timeline["scenes"][-1]["events"][0]["atFrame"])
            storyboard_source = root / "storyboard.json"
            storyboard_source.write_text(json.dumps(storyboard), encoding="utf-8")
            _add_storyboard(workspace, job, "en", storyboard_source)
            with patch("vidkit.cli.library.entries", return_value=library.entries(Workspace(ROOT))), \
                    patch("vidkit.cli.checkpoints.current_renderer_lock", return_value={"fixture": "hash"}), \
                    patch("vidkit.cli.sha256_file", return_value="hash"):
                _timeline(workspace, job, "en", False)
            stored = workspace.latest_artifact(job, K.TIMELINE, "en")
            self.assertEqual(stored["status"], S.CHECKED.value)
            self.assertEqual(json.loads(workspace.resolve_path(stored).read_text(encoding="utf-8"))
                             ["scenes"][-1]["componentProps"]["channelLabel"], "AI Lens")

    def test_concept_cta_uses_provisional_clicks_and_localized_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Topic", ["vi"], workflow_version=8)
            scenes = [{"id": role, "role": role, "component": "takeaway", "title": role,
                       "startMs": index * 1000, "endMs": (index + 1) * 1000}
                      for index, role in enumerate(("hook", "evidence", "takeaway"))]
            scenes.append({"id": "cta", "role": "cta", "component": "channel-cta",
                           "title": "Hiểu chủ đề", "startMs": 3000, "endMs": 7800,
                           "events": [{"id": "like-click", "atFrame": 900}]})
            workspace.add_json_artifact(job, "vi", K.BRIEF, {"theme": "dark-grid",
                "backgroundId": "grid-drift", "conceptPreview": {"scenes": scenes}}, S.CHECKED)
            prepared = []

            def prepare(_workspace, _job, _language, props, _audio):
                prepared.append(props)
                return Path(directory) / "props.json"

            def render(_root, _props, output, _entry):
                output.write_bytes(b"preview fixture")
                return 0

            def still(command, **_kwargs):
                Path(command[command.index("VidkitShort") + 1]).write_bytes(b"frame fixture")
                return type("Result", (), {"returncode": 0})()

            def show(_workspace, entry_id):
                result = {"id": entry_id, "version": "1", "sha256": "fixture", "style": {},
                          "loopSeconds": 8}
                return result

            with patch("vidkit.cli.library.show", side_effect=show), \
                    patch("vidkit.cli.prepare_renderer_job", side_effect=prepare), \
                    patch("vidkit.cli.visuals.render_entry", return_value=Path("src/index.ts")), \
                    patch("vidkit.cli.run_render", side_effect=render), \
                    patch("vidkit.cli.remotion_command", return_value=["remotion"]), \
                    patch("vidkit.cli.subprocess.run", side_effect=still), \
                    patch("vidkit.cli.checkpoints.current_renderer_lock", return_value={}):
                self.assertEqual(_concept_preview(workspace, job, "vi", None), 0)
            for props in prepared:
                cta = next(scene for scene in props["scenes"] if scene["role"] == "cta")
                self.assertEqual(cta["componentProps"]["channelLabel"], "HCDB AI")
                self.assertNotIn("events", cta)


if __name__ == "__main__":
    unittest.main()
