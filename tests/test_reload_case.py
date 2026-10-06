import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


case = load('reload_case', 'scripts/run-reload-case.py')
baseline = load('baseline', 'scripts/check-loaded-baseline.py')


class ReloadCaseTests(unittest.TestCase):
    def test_comparison_uses_verified_baseline_request_without_new_overrides(self):
        self.assertEqual(case.request_body(), baseline.request_body())

    def test_four_loads_each_followed_by_explicit_unload(self):
        events = []
        class FakeRunner:
            def generate(self, index):
                events.append(('load', index))
            def stop(self, index):
                events.append(('unload-confirmed', index))
        case.run_cycles(FakeRunner())
        self.assertEqual(events, [(action, i) for i in range(4) for action in ('load', 'unload-confirmed')])

    def test_failed_unload_prevents_next_generation(self):
        events = []
        class FakeRunner:
            def generate(self, index):
                events.append(index)
            def stop(self, index):
                raise RuntimeError('runner still present')
        with self.assertRaises(RuntimeError):
            case.run_cycles(FakeRunner())
        self.assertEqual(events, [0])

    def test_empty_api_list_is_not_enough_until_runner_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = case.CaseRunner('A', Path(directory))
            runner.attempted = True
            runner.event = lambda *args: None
            runner.capture = lambda *args, **kwargs: (0, '')
            runner.api = lambda *args: {'models': []}
            states = iter([True, False])
            runner.has_runner = lambda: next(states)
            with patch.object(case.time, 'sleep') as sleeping:
                runner.stop(0)
            sleeping.assert_called_once_with(1)
            self.assertFalse(runner.attempted)

    def test_rollback_makes_only_one_request_and_unloads_it(self):
        from unittest.mock import Mock
        runner = Mock()
        case.run_cycles(runner, loads=1)
        runner.generate.assert_called_once_with(0)
        runner.stop.assert_called_once_with(0)
        with tempfile.TemporaryDirectory() as directory:
            rollback = case.CaseRunner('E', Path(directory))
            self.assertEqual(rollback.container, 'ollama')
            self.assertEqual(rollback.base, 'http://127.0.0.1:11434')
            self.assertEqual(case.IMAGES['E'], case.IMAGES['A'])
