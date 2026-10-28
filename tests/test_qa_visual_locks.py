import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.storage import Workspace, sha256_file
from vidkit.workflow import make_qa


class QaVisualLockTests(unittest.TestCase):
    def test_job_visual_passes_until_its_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            job = workspace.create_job("Custom visual", ["en"], workflow_version=7)
            source = root / "Visual.tsx"
            source.write_text("original", encoding="utf-8")
            timeline = {
                "scenes": [{"id": "cta", "role": "cta", "startMs": 0,
                            "endMs": 1000, "visualAlignment": "centered"}],
                "componentLocks": [{"id": "job-visual", "version": "1.0.0",
                                    "sha256": sha256_file(source)}],
                "captions": [], "validationIssues": [], "missingAssets": [],
            }
            workspace.add_json_artifact(job, "en", K.TIMELINE, timeline, S.CHECKED)
            preview = root / "preview.mp4"
            preview.write_bytes(b"fixture")
            workspace.add_file_artifact(job, "en", K.PREVIEW, preview, S.NEEDS_REVIEW)

            def job_entries(actual_workspace, actual_job, language):
                self.assertIs(actual_workspace, workspace)
                self.assertEqual((actual_job, language), (job, "en"))
                return [{"id": "job-visual", "version": "1.0.0",
                         "sha256": sha256_file(source)}]

            with patch("vidkit.library.entries", return_value=[]), \
                    patch("vidkit.visuals.entries", side_effect=job_entries), \
                    patch("vidkit.workflow.shutil.which", return_value=None):
                for content, expected in [("original", "pass"), ("changed", "fail")]:
                    source.write_text(content, encoding="utf-8")
                    report = make_qa(workspace, job, "en")
                    data = json.loads(workspace.resolve_path(report).read_text(encoding="utf-8"))
                    self.assertEqual(data["checks"]["automatic"]["status"], expected)


if __name__ == "__main__":
    unittest.main()
