"""unit tests of the base module"""
import unittest
from unittest import mock
from task_core import base

DUMMY_FILE_DATA_ID = """
---
id: foo
"""

DUMMY_FILE_DATA_NAME = """
---
name: bar
"""


class TestBase(unittest.TestCase):
    """Test base file data object"""

    def test_file_data(self):
        """test data and name from id"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_FILE_DATA_ID)
        ) as open_mock:
            obj = base.BaseFileData("/foo/bar")
            open_mock.assert_called_with("/foo/bar")
            self.assertEqual(obj.data, {"id": "foo"})

    def test_file_data_name(self):
        """test data and name from name"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_FILE_DATA_NAME)
        ) as open_mock:
            obj = base.BaseFileData("/foo/bar")
            open_mock.assert_called_with("/foo/bar")
            self.assertEqual(obj.data, {"name": "bar"})
            self.assertEqual(obj.name, "bar")
