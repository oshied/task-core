"""unit tests of the inventory module"""
import unittest
from unittest import mock
from task_core import inventory
from task_core import exceptions as ex

DUMMY_INVENTORY_DATA = """
hosts:
  host-a:
    role: keystone
  host-b:
    role: basic
"""

DUMMY_ROLES_DATA = """
basic:
  services:
    - chronyd
    - repos
keystone:
  services:
    - chronyd
    - repos
    - mariadb
    - openstack-keystone
"""


class TestInventory(unittest.TestCase):
    """Test Inventory object"""

    def setUp(self):
        super().setUp()
        validator_patcher = mock.patch(
            "task_core.schema.InventorySchemaValidator.instance"
        )
        self.mock_validator = validator_patcher.start()
        self.addCleanup(validator_patcher.stop)
        isfile_patcher = mock.patch("os.path.isfile", return_value=True)
        self.mock_isfile = isfile_patcher.start()
        self.addCleanup(isfile_patcher.stop)

    def test_file_data(self):
        """test inventory file"""
        hosts = {"host-a": {"role": "keystone"}, "host-b": {"role": "basic"}}

        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_INVENTORY_DATA)
        ) as open_mock:
            obj = inventory.Inventory("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertEqual(obj.data, {"hosts": hosts})
            self.assertEqual(obj.hosts, hosts)
            self.assertEqual(obj.get_role_hosts(), hosts.keys())
            self.mock_validator.assert_called_once()

    def test_role_filter(self):
        """test getting hosts by role"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_INVENTORY_DATA)
        ) as open_mock:
            obj = inventory.Inventory("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertEqual(obj.get_role_hosts("keystone"), ["host-a"])


class TestRoles(unittest.TestCase):
    """Test Roles object"""

    def setUp(self):
        super().setUp()
        validator_patcher = mock.patch("task_core.schema.RolesSchemaValidator.instance")
        self.mock_validator = validator_patcher.start()
        self.addCleanup(validator_patcher.stop)
        isfile_patcher = mock.patch("os.path.isfile", return_value=True)
        self.mock_isfile = isfile_patcher.start()
        self.addCleanup(isfile_patcher.stop)

    def test_file_data(self):
        """test roles file"""

        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_ROLES_DATA)
        ) as open_mock:
            obj = inventory.Roles("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            # todo: data
            self.assertEqual(obj.roles, {"basic": mock.ANY, "keystone": mock.ANY})
            self.assertTrue(isinstance(obj.roles.get("basic"), inventory.Role))
            self.assertTrue(isinstance(obj.roles.get("keystone"), inventory.Role))
            self.assertEqual(obj.get_services("basic"), ["chronyd", "repos"])
            self.mock_validator.assert_called_once()

    def test_missing_role(self):
        """test roles file"""

        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_ROLES_DATA)
        ) as open_mock:
            obj = inventory.Roles("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertRaises(ex.InvalidRole, obj.get_services, "doesnotexist")


class TestRole(unittest.TestCase):
    """Test Role object"""

    def test_role(self):
        """test role object"""
        obj = inventory.Role("foo", ["bar"])
        self.assertEqual(obj.name, "foo")
        self.assertEqual(obj.services, ["bar"])
