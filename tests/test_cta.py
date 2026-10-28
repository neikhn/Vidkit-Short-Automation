import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vidkit.cli import _add_script, build_parser
from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.script_bundle import validate_script_bundle
from vidkit.storage import Workspace
from vidkit.timeline import compile_storyboard, validate_storyboard_shape
from vidkit.workflow import add_brief


DEVELOPMENT = {"understanding": "Ask for a useful next topic", "object": "Question",
               "action": "Reveal it", "result": "Readable CTA", "connection": "End the video"}


class CtaTests(unittest.TestCase):
    def test_new_cli_jobs_use_v10_but_existing_workspace_api_stays_v4(self):
        args = build_parser().parse_args(["create", "Topic"])
        self.assertEqual(args.workflow_version, 10)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            old = workspace.create_job("Existing", ["vi"])
            self.assertEqual(workspace.get_job(old)["workflow_version"], 4)

    def test_script_cta_is_spoken_and_ends_the_narration(self):
        spoken = "Theo dõi kênh và bình luận: Bạn muốn xem gì tiếp theo?"
        script = {"editorial_text": "Giải thích. " + spoken,
                  "expected_spoken_text": "Giải thích. " + spoken,
                  "tts_input": "Giải thích. " + spoken,
                  "cta": {"spokenText": spoken, "commentQuestion": "Bạn muốn xem gì tiếp theo?"}}
        self.assertEqual(validate_script_bundle(script, require_cta=True), [])
        self.assertEqual(validate_script_bundle({key: value for key, value in script.items() if key != "cta"}), [])
        self.assertTrue(validate_script_bundle({key: value for key, value in script.items() if key != "cta"}, require_cta=True))
        script["expected_spoken_text"] += " Câu khác."
        self.assertIn("expected_spoken_text must end", " ".join(validate_script_bundle(script, require_cta=True)))

    def test_v5_script_import_requires_cta_without_affecting_v4(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            v4 = workspace.create_job("Old", ["vi"])
            v5 = workspace.create_job("New", ["vi"], workflow_version=5)
            source = Path(directory) / "script.json"
            source.write_text(json.dumps({"editorial_text": "Xin chào.", "expected_spoken_text": "Xin chào.",
                                          "tts_input": "Xin chào."}), encoding="utf-8")
            _add_script(workspace, v4, "vi", source)
            with self.assertRaisesRegex(ValueError, "v5 script needs cta"):
                _add_script(workspace, v5, "vi", source)

    def test_v5_concept_requires_a_final_cta_scene(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("New", ["vi"], workflow_version=5)
            workspace.add_json_artifact(job, "vi", K.SCRIPT,
                {"cta": {"commentQuestion": "Bạn muốn xem gì tiếp theo?"}}, S.CHECKED)
            brief = {"angle": "Explain one feature", "theme": "dark-grid", "hook": "Why it matters",
                     "visualStrategy": "Show one process", "beats": [{"id": "beat-1", "development": DEVELOPMENT,
                     "approach": "custom"}], "explanationAlternatives": ["flow", "example"],
                     "chosenExplanation": "flow", "conceptPreview": {"scenes": [
                         {"id": role, "role": role, "component": "takeaway", "startMs": index * 1000,
                          "endMs": (index + 1) * 1000}
                         for index, role in enumerate(("hook", "evidence", "takeaway"))]}}
            source = Path(directory) / "brief.json"
            source.write_text(json.dumps(brief), encoding="utf-8")
            with patch("vidkit.library.entries", return_value=[{"kind": "theme", "id": "dark-grid"}]):
                with self.assertRaisesRegex(ValueError, "final CTA"):
                    add_brief(workspace, job, "vi", source)
                brief["conceptPreview"]["scenes"].append({"id": "cta", "role": "cta",
                    "component": "cta-end-card", "layout": "custom", "title": "Bạn muốn xem gì tiếp theo?",
                    "body": "Theo dõi kênh", "startMs": 3000, "endMs": 6000})
                source.write_text(json.dumps(brief), encoding="utf-8")
                self.assertEqual(add_brief(workspace, job, "vi", source)["revision"], 1)

    def test_v5_storyboard_cta_is_last_and_timed_from_words(self):
        words = [{"text": "Explain", "start": 0, "end": .5},
                 {"text": "it", "start": .6, "end": 1},
                 {"text": "Follow", "start": 1.5, "end": 2},
                 {"text": "and", "start": 2.1, "end": 2.4},
                 {"text": "comment", "start": 2.5, "end": 3.5}]
        storyboard = {"schemaVersion": 4, "theme": "dark-grid", "scenes": [
            {"id": "explanation", "layout": "takeaway", "title": "Explanation",
             "development": DEVELOPMENT, "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 1}},
            {"id": "cta", "role": "cta", "layout": "custom", "component": "cta-end-card",
             "title": "What should we cover next?", "body": "Follow and comment",
             "development": DEVELOPMENT, "startAnchor": {"wordIndex": 2}, "endAnchor": {"wordIndex": 4}}]}
        transcript = {"words": words, "durationSeconds": 4}
        self.assertEqual(validate_storyboard_shape(storyboard, require_cta=True), [])
        timeline, missing = compile_storyboard(transcript, storyboard, {"assets": []},
                                               "Topic", "en", "voice.mp3", require_cta=True)
        self.assertEqual(missing, [])
        self.assertEqual((timeline["scenes"][-1]["role"], timeline["scenes"][-1]["startMs"]), ("cta", 1500))
        self.assertEqual(validate_storyboard_shape({**storyboard, "scenes": storyboard["scenes"][:1]}), [])
        self.assertTrue(validate_storyboard_shape({**storyboard, "scenes": storyboard["scenes"][:1]}, require_cta=True))
        short_words = [dict(word) for word in words]
        short_words[2].update(start=2.3, end=2.4)
        short_words[3].update(start=2.5, end=2.7)
        short_words[4].update(start=3, end=3.5)
        with self.assertRaisesRegex(ValueError, "at least 2 seconds"):
            compile_storyboard({"words": short_words, "durationSeconds": 4}, storyboard,
                               {"assets": []}, "Topic", "en", "voice.mp3", require_cta=True)

    def test_cta_component_has_a_fixture_without_a_production_job(self):
        root = Path(__file__).resolve().parents[1] / "renderer" / "library"
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        component = next(item for item in manifest["components"] if item["id"] == "cta-end-card")
        self.assertTrue((root / component["codePath"] / component["entrypoint"]).is_file())
        fixture = json.loads((root / component["preview"]).read_text(encoding="utf-8"))
        self.assertEqual(fixture["scenes"][-1]["componentId"], "cta-end-card")


if __name__ == "__main__":
    unittest.main()
