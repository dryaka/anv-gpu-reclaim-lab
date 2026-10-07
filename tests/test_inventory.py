import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inventory", ROOT / "scripts/collect-inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_arbitrary_secrets_and_full_configuration_are_excluded(self):
        original = {
            "Image": "sha256:abc", "Config": {
                "Env": ["HTTP_PROXY=http://user:proxysecret@proxy", "TOKEN=secret-token",
                        "OLLAMA_CONTEXT_LENGTH=32768", "OLLAMA_HOST=http://user:hostsecret@localhost:11434"],
                "Cmd": ["--api-key", "commandsecret"], "Labels": {"token": "labelsecret"}},
            "HostConfig": {"Memory": 1024, "UnknownSensitiveField": "othersecret"},
        }
        result = inventory.summarize_inspect(original)
        encoded = json.dumps(result)
        for value in ("proxysecret", "secret-token", "hostsecret", "commandsecret", "labelsecret", "othersecret"):
            self.assertNotIn(value, encoded)
        self.assertEqual(result["environment"]["OLLAMA_CONTEXT_LENGTH"], "32768")
        self.assertEqual(result["host_config"]["Memory"], 1024)
        self.assertIsNone(result["environment"]["ANV_SYS_MEM_LIMIT"])

    def test_environment_preserves_equals_and_unset_values(self):
        result = inventory.selected_environment(["VK_DRIVER_FILES=/a=b/icd.json", "ANV_SYS_MEM_LIMIT=90"])
        self.assertEqual(result["VK_DRIVER_FILES"], "/a=b/icd.json")
        self.assertEqual(result["ANV_SYS_MEM_LIMIT"], "90")
        self.assertIsNone(result["VK_ICD_FILENAMES"])

    def test_stopped_container_is_not_started_or_probed(self):
        calls = []

        def fake_run(argv, timeout=30):
            calls.append(argv)
            stdout = ""
            if argv[:4] == ["podman", "inspect", "--type", "container"]:
                stdout = json.dumps([{"Image": "sha256:abc", "State": {"Running": False},
                                      "Config": {"Env": ["TOKEN=secret-token"]}}])
            elif argv[:3] == ["podman", "image", "inspect"]:
                stdout = json.dumps([{"Id": "sha256:abc", "RepoDigests": ["example/image@sha256:abc"],
                                      "Config": {"Env": ["TOKEN=image-secret"]}}])
            return {"returncode": 0, "stdout": stdout, "stderr": ""}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-evidence"
            with patch.object(sys, "argv", ["collector", "--output", str(output)]), \
                    patch.object(inventory, "run", fake_run), \
                    patch.object(inventory, "read_text", return_value=""), \
                    contextlib.redirect_stdout(io.StringIO()):
                inventory.main()
            report = json.loads((output / "inventory.json").read_text())
            self.assertIn("skipped", report["container_probe"])
            self.assertNotIn("secret-token", json.dumps(report))
            self.assertNotIn("image-secret", json.dumps(report))
            self.assertEqual((output / "inventory.json").stat().st_mode & 0o777, 0o600)
        self.assertFalse(any(command[:2] in (["podman", "start"], ["podman", "stop"], ["podman", "exec"])
                             for command in calls))

    def test_failed_inspect_never_writes_unfiltered_output(self):
        def fake_run(argv, timeout=30):
            return {"returncode": 1, "stdout": "unfiltered-secret", "stderr": "unfiltered-secret"} \
                if argv[:2] == ["podman", "inspect"] else {"returncode": 0, "stdout": "", "stderr": ""}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-evidence"
            with patch.object(sys, "argv", ["collector", "--output", str(output)]), \
                    patch.object(inventory, "run", fake_run), \
                    patch.object(inventory, "read_text", return_value=""), \
                    contextlib.redirect_stdout(io.StringIO()):
                inventory.main()
            report = (output / "inventory.json").read_text()
            self.assertNotIn("unfiltered-secret", report)
            self.assertIn("inspect_error", report)

    def test_timeout_does_not_leak_partial_output(self):
        with patch.object(inventory.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                ["podman", "inspect"], 30, output="timeout-secret")):
            result = inventory.run(["podman", "inspect", "ollama"])
        self.assertEqual(result["error"], "TimeoutExpired")
        self.assertNotIn("timeout-secret", json.dumps(result))

    def test_container_shell_probe_syntax(self):
        subprocess.run(["sh", "-n"], input=inventory.CONTAINER_PROBE, text=True, check=True)


if __name__ == "__main__":
    unittest.main()
