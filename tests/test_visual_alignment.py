import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vidkit.cli import build_parser
from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.storage import Workspace
from vidkit.timeline import compile_storyboard
from vidkit.workflow import make_qa


class VisualAlignmentTests(unittest.TestCase):
    def test_new_jobs_use_v10_and_old_timeline_keeps_legacy_layout(self):
        self.assertEqual(build_parser().parse_args(["create", "Topic"]).workflow_version, 10)
        words = [{"text": "Hello", "start": 0, "end": .5}]
        storyboard = {"schemaVersion": 4, "theme": "dark-grid", "scenes": [{
            "id": "hook", "layout": "brand-hook", "title": "Hello",
            "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 0}}]}
        args = ({"words": words}, storyboard, {"assets": []}, "Topic", "en", "voice.mp3")
        old, _ = compile_storyboard(*args)
        new, _ = compile_storyboard(*args, center_visuals=True)
        self.assertNotIn("visualAlignment", old["scenes"][0])
        self.assertEqual(new["scenes"][0]["visualAlignment"], "centered")

    def test_qa_alignment_is_not_run_until_inspected_and_failures_name_scene_and_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("New", ["en"], workflow_version=6)
            timeline = {"scenes": [
                {"id": "hook", "startMs": 0, "endMs": 2000, "visualAlignment": "centered"},
                {"id": "cta", "role": "cta", "startMs": 2000, "endMs": 4000,
                 "visualAlignment": "centered"}], "captions": [], "validationIssues": [], "missingAssets": []}
            workspace.add_json_artifact(job, "en", K.TIMELINE, timeline, S.CHECKED)
            preview = Path(directory) / "preview.mp4"
            preview.write_bytes(b"fixture")
            workspace.add_file_artifact(job, "en", K.PREVIEW, preview, S.NEEDS_REVIEW)
            with patch("vidkit.workflow.shutil.which", return_value=None):
                report = make_qa(workspace, job, "en")
                data = json.loads(workspace.resolve_path(report).read_text(encoding="utf-8"))
                self.assertEqual(data["checks"]["visualAlignment"]["status"], "not-run")
                finding = {"sceneId": "hook", "frame": 30, "note": "Logo group is left of center"}
                report = make_qa(workspace, job, "en", {"checks": {"visualAlignment": {
                    "status": "fail", "evidence": [finding]}}})
                data = json.loads(workspace.resolve_path(report).read_text(encoding="utf-8"))
                self.assertEqual(data["checks"]["visualAlignment"]["evidence"], [finding])
                with self.assertRaisesRegex(ValueError, "frame must belong"):
                    make_qa(workspace, job, "en", {"checks": {"visualAlignment": {
                        "status": "fail", "evidence": [{**finding, "frame": 90}]}}})

    def test_fixture_covers_logo_cards_branches_chart_and_captions(self):
        root = Path(__file__).resolve().parents[1] / "renderer"
        fixture = json.loads((root / "library/fixtures/visual-centering.json").read_text(encoding="utf-8"))
        self.assertEqual([scene["id"] for scene in fixture["scenes"]],
                         ["logo", "cards", "diagram", "chart"])
        self.assertTrue(all(scene["visualAlignment"] == "centered" for scene in fixture["scenes"]))
        self.assertEqual(len(fixture["captions"]), 4)
        self.assertTrue((root / "public/fixtures/alignment-mark.svg").is_file())


if __name__ == "__main__":
    unittest.main()
