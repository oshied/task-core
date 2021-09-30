"""unit tests of the base module"""
import unittest
import yaml
from unittest import mock
from taskflow.types import sets
from task_core import base
from task_core.exceptions import InvalidFileData

DUMMY_FILE_DATA_ID = """
---
id: foo
"""

DUMMY_FILE_DATA_NAME = """
---
name: bar
"""


class TestBaseFileData(unittest.TestCase):
    """Test base file data object"""

    @mock.patch("os.path.isfile", return_value=True)
    def test_file_data(self, mock_isfile):
        """test data and name from id"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_FILE_DATA_ID)
        ) as open_mock:
            obj = base.BaseFileData("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertEqual(obj.data, {"id": "foo"})

    @mock.patch("os.path.isfile", return_value=True)
    def test_file_data_name(self, mock_isfile):
        """test data and name from name"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_FILE_DATA_NAME)
        ) as open_mock:
            obj = base.BaseFileData("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertEqual(obj.data, {"name": "bar"})
            self.assertEqual(obj.name, "bar")

    @mock.patch("glob.glob", return_value=["/foo/bar/a.yaml", "/foo/bar/b.yaml"])
    @mock.patch("os.path.isdir", return_value=True)
    @mock.patch("os.path.isfile", return_value=False)
    def test_file_data_directory(self, mock_isfile, mock_isdir, mock_glob):
        """test data and name from name"""
        with mock.patch("builtins.open", mock.mock_open()) as open_mock:
            mock_files = [
                mock.mock_open(read_data=content).return_value
                for content in [DUMMY_FILE_DATA_ID, DUMMY_FILE_DATA_NAME]
            ]
            open_mock.side_effect = mock_files
            obj = base.BaseFileData("/foo/bar")
            open_calls = [
                mock.call("/foo/bar/a.yaml", encoding="utf-8", mode="r"),
                mock.call("/foo/bar/b.yaml", encoding="utf-8", mode="r"),
            ]
            open_mock.assert_has_calls(open_calls)
            self.assertEqual(obj.data, {"id": "foo", "name": "bar"})
            self.assertEqual(obj.name, "foo")

    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch("os.path.isfile", return_value=False)
    def test_file_data_dict(self, mock_isfile, mock_isdir):
        """test data with a dictionary"""
        obj = base.BaseFileData(yaml.safe_load(DUMMY_FILE_DATA_NAME))
        self.assertEqual(obj.data, {"name": "bar"})
        self.assertEqual(obj.name, "bar")

    @mock.patch("os.path.isdir", return_value=False)
    @mock.patch("os.path.isfile", return_value=False)
    def test_file_data_invalid(self, mock_isfile, mock_isdir):
        """test data with invalid definition"""
        self.assertRaises(InvalidFileData, base.BaseFileData, 1)


class TestBaseTask(unittest.TestCase):
    """Test base task object"""

    def test_base_task(self):
        obj = base.BaseTask("test", {"id": "i", "action": "a"}, [])
        self.assertEqual(obj.data, {"id": "i", "action": "a"})
        self.assertEqual(obj.hosts, [])
        self.assertEqual(obj.service, "test")
        self.assertEqual(obj.task_id, "i")
        self.assertEqual(obj.action, "a")
        self.assertRaises(NotImplementedError, obj.execute)

    def test_deps(self):
        data = {
            "id": "i",
            "action": "a",
            "driver": "print",
            "provides": ["foo"],
            "requires": ["bar"],
            "needed-by": ["baz"],
        }
        obj = base.BaseTask("test", data, [])
        self.assertEqual(obj.driver, "print")
        self.assertEqual(obj.task_provides, ["foo"])
        self.assertEqual(obj.task_requires, ["bar"])
        self.assertEqual(obj.task_needed_by, ["baz"])
        self.assertEqual(obj.requires, sets.OrderedSet(["bar"]))
        obj.update_requires(["buzz"])
        self.assertEqual(obj.requires, sets.OrderedSet(["bar", "buzz"]))


class TestBaseInstance(unittest.TestCase):
    """Test BaseInstance object"""

    def test_base_instance(self):
        obj = base.BaseInstance.instance()
        self.assertIsInstance(obj, base.BaseInstance)
        self.assertRaises(RuntimeError, base.BaseInstance)
