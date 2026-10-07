import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('memory_case', Path(__file__).resolve().parents[1] / 'scripts/run-memory-case.py')
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryCaseTests(unittest.TestCase):
    def test_one_measured_reload_with_initial_loaded_state(self):
        events = []
        class FakeRunner:
            def generate(self, index):
                events.append(('load', index))
            def stop(self, index):
                events.append(('stop-confirmed', index))
        memory.run_sequence(FakeRunner())
        self.assertEqual(events, [('load', 0), ('stop-confirmed', 0), ('load', 1), ('stop-confirmed', 1)])

    def test_failed_unload_prevents_background_test_reload(self):
        runner = Mock()
        runner.stop.side_effect = RuntimeError('runner still alive')
        with self.assertRaises(RuntimeError):
            memory.run_sequence(runner)
        runner.generate.assert_called_once_with(0)

    def test_holder_cleanup_escalates_after_timeout(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [memory.subprocess.TimeoutExpired('holder', 10), 0]
        memory.stop_holder(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()

    def test_holder_exits_after_parent_death_with_bounded_touched_memory(self):
        # Exercise real anonymous mapping/touch logic using a small test allocation.
        from unittest.mock import patch
        import io
        output = io.StringIO()
        with patch.object(memory, 'HOLDER_BYTES', 1024 * 1024), \
             patch.object(memory.os, 'getppid', side_effect=[100, 1]), \
             patch.object(memory.sys, 'stdout', output):
            memory.holder()
        self.assertEqual(memory.json.loads(output.getvalue())['allocated_bytes'], 1024 * 1024)
