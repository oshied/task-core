"""unit tests of the utils"""
import unittest
from task_core import utils


class TestUtils(unittest.TestCase):
    """Test utils module"""

    def test_merge_dict(self):
        """test merge dict without extend"""
        base = {
            "a": 1,
            "b": "2",
            "c": [3],
            "d": {"x": "y", "z": None},
            "f": set((1, 2)),
            "t": tuple((1, 2)),
            "l": [2, 3],
            "m": [{"n": "m"}],
        }
        to_merge = {
            "c": [4],
            "e": "4",
            "d": {"y": "foo", "z": "bar"},
            "f": set((2, 3)),
            "t": tuple((2, 3)),
            "l": set((1, 2)),
            "m": [{"n": "o"}],
        }
        expected = {
            "a": 1,
            "b": "2",
            "c": [4],
            "e": "4",
            "d": {"x": "y", "y": "foo", "z": "bar"},
            "f": set((2, 3)),
            "t": tuple((2, 3)),
            "l": set((1, 2)),
            "m": [{"n": "o"}],
        }
        self.assertEqual(utils.merge_dict(base, to_merge), expected)

    def test_merge_dict_extend(self):
        """test merge dict with extend"""
        base = {
            "a": 1,
            "b": "2",
            "c": [3],
            "d": {"x": "y", "z": None},
            "f": set((1, 2)),
            "t": tuple((1, 2)),
            "l": [2, 3],
            "m": [{"n": "m"}],
        }
        to_merge = {
            "c": [4],
            "e": "4",
            "d": {"y": "foo", "z": "bar"},
            "f": set((2, 3)),
            "t": tuple((2, 3)),
            "l": set((1, 2)),
            "m": [{"n": "o"}],
        }
        expected = {
            "a": 1,
            "b": "2",
            "c": [3, 4],
            "e": "4",
            "f": set((1, 2, 3)),
            "d": {"x": "y", "y": "foo", "z": "bar"},
            "t": tuple((1, 2, 2, 3)),
            "l": [2, 3, 1, 2],
            "m": [{"n": "m"}, {"n": "o"}],
        }
        self.assertEqual(utils.merge_dict(base, to_merge, True), expected)

    def test_merge_dict_list(self):
        """test merge list into dict"""
        base = {"a": "b"}
        to_merge = ["x"]
        self.assertRaises(Exception, utils.merge_dict, base, to_merge)
