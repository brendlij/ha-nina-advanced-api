"""Regression coverage using Advanced API's Smart Exposure payload shape."""
import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).parents[1] / "custom_components/nina_api/sequence.py"
spec = importlib.util.spec_from_file_location("nina_sequence", path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
summarize = module.summarize_sequence


class SequenceTests(unittest.TestCase):
    def test_smart_exposure_unnamed_running_leaf(self):
        result = summarize([{"Name": "Targets_Container", "Status": "RUNNING", "Items": [
            {"Name": "Smart Exposure_Container", "Status": "RUNNING", "Items": [
                {"Name": None, "Status": "SKIPPED"},
                {"Name": None, "Status": "RUNNING", "ExposureTime": 120},
            ]},
        ]}])
        self.assertTrue(result.running)
        self.assertEqual(result.current_item, "Smart Exposure")
        self.assertEqual((result.total, result.finished), (2, 1))

    def test_container_running_between_steps(self):
        result = summarize([{"Name": "Target_Container", "Status": "RUNNING", "Items": [
            {"Name": "Exposure", "Status": "FINISHED"},
        ]}])
        self.assertTrue(result.running)
        self.assertEqual(result.current_item, "Target")

    def test_empty_running_container(self):
        result = summarize([{"Name": "Target_Container", "Status": "RUNNING", "Items": []}])
        self.assertTrue(result.running)
        self.assertEqual(result.total, 0)

    def test_named_child_is_preferred(self):
        result = summarize([{"Name": "Target_Container", "Status": "RUNNING", "Items": [
            {"Name": "Autofocus", "Status": "RUNNING"},
        ]}])
        self.assertEqual(result.current_item, "Autofocus")

    def test_idle_finished_and_triggers_are_not_running(self):
        result = summarize([None, {"GlobalTriggers": [{"Status": "RUNNING"}]},
            {"Name": "End_Container", "Status": "CREATED", "Items": []},
            {"Name": "Exposure", "Status": "FINISHED"}])
        self.assertFalse(result.running)
        self.assertIsNone(result.current_item)
        self.assertEqual((result.total, result.finished), (1, 1))

    def test_no_name_anywhere_still_running(self):
        result = summarize([{"Name": None, "Status": "RUNNING"}])
        self.assertTrue(result.running)
        self.assertEqual(result.current_item, "Running instruction")


if __name__ == "__main__":
    unittest.main()
