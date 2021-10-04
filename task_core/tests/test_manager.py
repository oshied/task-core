"""unit tests of the manager module"""
import unittest
from unittest import mock
from task_core.manager import TaskManager
from task_core.exceptions import InvalidService


class TestTaskManager(unittest.TestCase):
    """Test task manager"""

    def setUp(self):
        super().setUp()
        isdir_patcher = mock.patch("os.path.isdir")
        isfile_patcher = mock.patch("os.path.isfile")
        self.mock_isdir = isdir_patcher.start()
        self.addCleanup(isdir_patcher.stop)
        self.mock_isfile = isfile_patcher.start()
        self.addCleanup(isfile_patcher.stop)

    @mock.patch("task_core.manager.TaskManager.load")
    def test_manager_init(self, mock_load):
        """Test init logic"""
        self.mock_isdir.return_value = True
        self.mock_isfile.side_effect = [True, True]
        mgr = TaskManager("a", "b", "c", True)
        self.assertEqual(mgr.services_dir, "a")
        self.assertEqual(mgr.inventory_file, "b")
        self.assertEqual(mgr.roles_file, "c")

        self.mock_isdir.return_value = True
        self.mock_isfile.side_effect = [True, True]
        mgr = TaskManager("a", "b", "c")
        mock_load.assert_called_once_with()

        self.mock_isdir.return_value = False
        self.mock_isfile.side_effect = [True, True]
        self.assertRaises(Exception, TaskManager, "a", "b", "c")

        self.mock_isdir.return_value = True
        self.mock_isfile.side_effect = [False, True]
        self.assertRaises(Exception, TaskManager, "a", "b", "c")

        self.mock_isdir.return_value = True
        self.mock_isfile.side_effect = [True, False]
        self.assertRaises(Exception, TaskManager, "a", "b", "c")

    # NOTE(mwhahaha): because I'll forget this,
    # https://docs.python.org/3/library/unittest.mock.html#where-to-patch
    @mock.patch("task_core.manager.Roles", autospec=True)
    @mock.patch("task_core.manager.Inventory", autospec=True)
    @mock.patch("task_core.manager.Service", autospec=True)
    def test_manager_load(self, mock_svc, mock_inv, mock_roles):
        self.mock_isdir.return_value = True
        self.mock_isfile.return_value = True
        mgr = TaskManager("a", "b", "c")
        self.assertEqual(mgr.services_dir, "a")
        self.assertEqual(mgr.inventory_file, "b")
        self.assertEqual(mgr.roles_file, "c")

    @mock.patch("task_core.manager.Service", autospec=True)
    @mock.patch("glob.glob")
    def test_manager_load_services(self, mock_glob, mock_svc):
        self.mock_isdir.return_value = True
        self.mock_isfile.return_value = True
        mock_resolve = mock.MagicMock()
        mock_svc.return_value.name = "svc"
        mock_glob.return_value = ["a/svc.yaml"]

        mgr = TaskManager("a", "b", "c", True)
        mgr.resolve_service_deps = mock_resolve
        mgr.load_services()

        mock_svc.assert_called_with("a/svc.yaml")
        self.assertEqual(mgr.services, {"svc": mock_svc.return_value})
        mock_resolve.assert_called_once_with()

    @mock.patch("task_core.manager.Service", autospec=True)
    @mock.patch("glob.glob")
    def test_manager_load_services_fail(self, mock_glob, mock_svc):
        self.mock_isdir.return_value = True
        self.mock_isfile.return_value = True
        mock_resolve = mock.MagicMock()
        mock_svc.side_effect = Exception("fail")
        mock_glob.return_value = ["a/svc.yaml"]

        mgr = TaskManager("a", "b", "c", True)
        mgr.resolve_service_deps = mock_resolve
        self.assertRaises(Exception, mgr.load_services)

        mock_svc.assert_called_with("a/svc.yaml")
        self.assertEqual(mgr.services, {})
        mock_resolve.assert_not_called()

    def test_manager_resolve_service_deps(self):
        mock_svc_obj = mock.MagicMock()
        mock_svc_obj.get_tasks_needed_by.side_effect = [{}, {"c": ["b"]}, {"a": ["c"]}]
        mock_update = mock.MagicMock()
        mock_svc_obj.update_task_requires = mock_update
        svcs = {"a": mock_svc_obj, "b": mock_svc_obj, "c": mock_svc_obj}
        mgr = TaskManager("a", "b", "c", True)
        mgr.services = svcs
        mgr.resolve_service_deps()
        needed_by = {"c": ["b"], "a": ["c"]}
        update_calls = [
            mock.call(needed_by),
            mock.call(needed_by),
            mock.call(needed_by),
        ]
        self.assertEqual(mock_update.mock_calls, update_calls)

    def test_manager_hosts_to_services(self):
        mgr = TaskManager("a", "b", "c", True)
        mgr.inventory = mock.MagicMock()
        mgr.inventory.hosts = {
            "host-0": {"role": "role-a"},
            "host-1": {"role": "role-b"},
        }
        mgr.roles = mock.MagicMock()
        mock_get_svcs = mock.MagicMock()
        mock_get_svcs.side_effect = [["svc-a"], ["svc-b"]]
        mgr.roles.get_services = mock_get_svcs
        mock_svc = mock.MagicMock()
        mock_add_host = mock.MagicMock()
        mock_svc.add_host = mock_add_host
        mgr.services = {"svc-a": mock_svc, "svc-b": mock_svc}
        mgr.hosts_to_services()
        self.assertEquals(
            mock_get_svcs.mock_calls, [mock.call("role-a"), mock.call("role-b")]
        )
        self.assertEquals(
            mock_add_host.mock_calls, [mock.call("host-0"), mock.call("host-1")]
        )

    def test_manager_hosts_to_services_fail(self):
        mgr = TaskManager("a", "b", "c", True)
        mgr.inventory = mock.MagicMock()
        mgr.inventory.hosts = {
            "host-0": {"role": "role-a"},
            "host-1": {"role": "role-b"},
        }
        mgr.roles = mock.MagicMock()
        mock_get_svcs = mock.MagicMock()
        mock_get_svcs.return_value = ["svc-c"]
        mgr.roles.get_services = mock_get_svcs
        mock_svc = mock.MagicMock()
        mock_add_host = mock.MagicMock()
        mock_svc.add_host = mock_add_host
        mgr.services = {"svc-a": mock_svc, "svc-b": mock_svc}
        self.assertRaises(InvalidService, mgr.hosts_to_services)
        self.assertEquals(mock_get_svcs.mock_calls, [mock.call("role-a")])
        mock_add_host.assert_not_called()

    @mock.patch("networkx.drawing.nx_pydot.to_pydot")
    def test_write_flow_graph(self, mock_nx):
        mock_dot = mock.MagicMock()
        mock_write = mock.MagicMock()
        mock_dot.write_svg = mock_write
        mock_nx.return_value = mock_dot
        mock_flow = mock.MagicMock()
        mock_flow._graph = {}
        mgr = TaskManager("a", "b", "c", True)
        mgr.write_flow_graph(mock_flow)
        mock_nx.assert_called_once_with({})
        mock_write.assert_called_once_with("output.svg")
