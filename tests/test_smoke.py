import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('smoke', Path(__file__).resolve().parents[1] / 'scripts/smoke-test.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeCaptureTests(unittest.TestCase):
    def test_non_utf8_logs_preserve_bytes_without_decoding_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            text = smoke.capture_command(out, 'container.log', [sys.executable, '-c',
                "import sys; sys.stdout.buffer.write(b'ANV\\xc4 log\\n')"], check=False)
            self.assertEqual((out / 'container.log').read_bytes(), b'ANV\xc4 log\n')
            self.assertEqual(text, 'ANV\ufffd log\n')

    def test_cleanup_timeout_keeps_partial_log_and_returns(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with patch.object(smoke.subprocess, 'run', side_effect=subprocess.TimeoutExpired('podman', 120, output=b'partial\xc4')):
                smoke.capture_command(out, 'container.log', ['podman', 'logs'], check=False)
            self.assertTrue((out / 'container.log').read_bytes().startswith(b'partial\xc4'))
