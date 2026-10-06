import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("baseline", ROOT / "scripts/check-loaded-baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class BaselineTests(unittest.TestCase):
    def test_existing_loaded_model_prevents_new_generation(self):
        paths = []

        def fake_api(path, payload=None):
            paths.append(path)
            return {"version": "0.34.4"} if path == "/api/version" else {"models": [{"name": "existing"}]}

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "evidence"
            with patch.object(sys, "argv", ["baseline", "--output", str(out)]), \
                    patch.object(baseline, "api", fake_api), \
                    patch.object(baseline.subprocess, "run") as process, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(baseline.main(), 1)
                process.assert_not_called()
            self.assertFalse(json.loads((out / "baseline.json").read_text())["request_completed"])
        self.assertNotIn("/api/generate", paths)

    def test_absent_model_is_not_pulled_or_generated(self):
        paths = []

        def fake_api(path, payload=None):
            paths.append(path)
            return {"version": "0.34.4"} if path == "/api/version" else {"models": []}

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sys, "argv", ["baseline", "--output", str(Path(directory) / "evidence")]), \
                    patch.object(baseline, "api", fake_api), \
                    patch.object(baseline.subprocess, "run") as process, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(baseline.main(), 1)
                process.assert_not_called()
        self.assertEqual(paths, ["/api/version", "/api/ps", "/api/tags"])

    def test_request_preserves_default_cpu_and_gpu_selection(self):
        request = baseline.request_body()
        self.assertEqual(request["options"]["num_ctx"], 32768)
        self.assertEqual(request["options"]["num_predict"], 128)
        for name in ("num_thread", "num_batch", "num_gpu", "main_gpu", "flash_attention"):
            self.assertNotIn(name, request["options"])

    def test_completed_request_collects_loaded_evidence_without_stopping(self):
        commands = []
        def fake_api(path, payload=None):
            if path == "/api/version": return {"version": "0.34.4"}
            if path == "/api/tags": return {"models": [{"name": baseline.MODEL}]}
            if path == "/api/ps": return {"models": []}
            return {"done": True, "eval_count": 10}
        def fake_command(argv, timeout):
            commands.append(argv)
            return {"returncode": 0, "stdout": "", "stderr": ""}
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "evidence"
            with patch.object(sys, "argv", ["baseline", "--output", str(out)]), \
                    patch.object(baseline, "api", fake_api), patch.object(baseline, "command", fake_command), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(baseline.main(), 0)
            self.assertTrue(json.loads((out / "baseline.json").read_text())["request_completed"])
            self.assertTrue((out / "memory-samples.json").exists())
            self.assertEqual((Path(directory) / "evidence.tar.gz").stat().st_mode & 0o777, 0o600)
        self.assertTrue(any("--output" in argv for argv in commands))
        self.assertTrue(any(argv[:2] == ["podman", "logs"] for argv in commands))
        self.assertFalse(any("stop" in argv or "pull" in argv for argv in commands))


if __name__ == "__main__":
    unittest.main()
