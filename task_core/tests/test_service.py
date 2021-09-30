"""unit tests of the service module"""
import unittest
import yaml
from unittest import mock
from task_core import service

DUMMY_SERVICE_DATA = """
id: service-a
type: service
version: 1.0.0
tasks:
  - id: print
    driver: print
    message: "message from service a"

  - id: setup
    action: init
    driver: service
    provides:
      - service-a.init
    jobs:
      - echo: "service a start"

  - id: run
    action: run
    driver: service
    provides:
      - service-a.run
    requires:
      - service-a.init
    needed-by:
      - service-b.run
    jobs:
      - echo: "service a run"

  - id: finalize
    action: finalize
    driver: service
    provides:
      - service-a.finalize
    requires:
      - service-a.run
    needed-by:
      - service-b.run
    jobs:
      - echo: "service a done"
"""


class TestService(unittest.TestCase):
    """Test Service object"""

    def setUp(self):
        super().setUp()
        taskmgr_patcher = mock.patch("task_core.tasks.TaskManager.instance")
        self.mock_tm_instance = taskmgr_patcher.start()
        self.addCleanup(taskmgr_patcher.stop)
        self.mock_taskmgr = mock.MagicMock()
        self.mock_tm_instance.return_value = self.mock_taskmgr
        validator_patcher = mock.patch(
            "task_core.schema.ServiceSchemaValidator.instance"
        )
        self.mock_validator = validator_patcher.start()
        self.addCleanup(validator_patcher.stop)
        isfile_patcher = mock.patch("os.path.isfile", return_value=True)
        self.mock_isfile = isfile_patcher.start()
        self.addCleanup(isfile_patcher.stop)

    def test_file_data(self):
        """test service file"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_SERVICE_DATA)
        ) as open_mock:
            obj = service.Service("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertEqual(obj.type, "service")
            self.assertEqual(obj.version, "1.0.0")
            self.assertEqual(obj.provides, "service-a")
            self.assertEqual(obj.requires, [])
            self.assertEqual(len(obj.tasks), 4)

    def test_hosts(self):
        """tests host add/remove"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_SERVICE_DATA)
        ) as open_mock:
            obj = service.Service("/hosts")
            open_mock.assert_called_with("/hosts", encoding="utf-8", mode="r")
            self.assertEqual(obj.hosts, [])
            self.assertEqual(obj.add_host("test"), ["test"])
            self.assertEqual(obj.remove_host("test"), [])

    def test_build_tasks(self):
        """test task building"""

        class TestTaskA:
            """test task type"""

            def __init__(self, name, task, hosts):
                self.name = name
                self.task = task
                self.hosts = hosts

        class TestTaskB(TestTaskA):
            """ "alternate test type"""

        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_SERVICE_DATA)
        ) as open_mock:
            obj = service.Service("/tasks")
            open_mock.assert_called_with("/tasks", encoding="utf-8", mode="r")
            self.mock_taskmgr.get_driver.return_value = TestTaskA
            ret = obj.build_tasks()
            self.assertEqual(len(ret), 4)
            for x in ret:
                self.assertTrue(isinstance(x, TestTaskA))
            ret = obj.build_tasks(TestTaskB)
            self.assertEqual(len(ret), 4)
            for x in ret:
                self.assertTrue(isinstance(x, TestTaskB))

    @mock.patch("yaml.dump")
    def test_save(self, mock_dump):
        """test save"""
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_SERVICE_DATA)
        ) as open_mock:
            obj = service.Service("/tasks")
            open_mock.assert_called_with("/tasks", encoding="utf-8", mode="r")
            obj.save("/tmp/foo")
            open_mock.assert_called_with("/tmp/foo", encoding="utf-8", mode="w")
            mock_dump.assert_called_with(yaml.safe_load(DUMMY_SERVICE_DATA), mock.ANY)

    def test_requires_update(self):
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_SERVICE_DATA)
        ) as open_mock:
            obj = service.Service("/foo/bar")
            open_mock.assert_called_with("/foo/bar", encoding="utf-8", mode="r")
            self.assertEqual(obj.tasks[3].get("requires"), ["service-a.run"])
            updates = {
                "service-a.init": None,
                "service-a.finalize": ["other-service.init"],
                "service-a.run": "other-service.foo",
            }
            obj.update_task_requires(updates)
            self.assertListEqual(
                sorted(obj.tasks[2].get("requires")),
                sorted(["service-a.init", "other-service.foo"]),
            )

            self.assertListEqual(
                sorted(obj.tasks[3].get("requires")),
                sorted(["service-a.run", "other-service.init"]),
            )

    def test_needed_by(self):
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=DUMMY_SERVICE_DATA)
        ) as open_mock:
            obj = service.Service("/example")
            open_mock.assert_called_with("/example", encoding="utf-8", mode="r")
            self.assertEqual(
                obj.get_tasks_needed_by(),
                {"service-b.run": sorted(["service-a.finalize", "service-a.run"])},
            )
