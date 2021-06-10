"""unit tests of tasks"""
import stevedore.exception
import unittest
import yaml
from unittest import mock
from task_core import tasks
from task_core.exceptions import ExecutionFailed


DUMMY_PRINT_TASK_DATA = """
id: print
driver: print
message: "message from service a"
"""

DUMMY_SERVICE_TASK_DATA = """
id: run
action: run
provides:
  - service-a.run
requires:
  - service-a.init
jobs:
  - echo: "service a run"
"""

DUMMY_DIRECTORD_SERVICE_TASK_DATA = """
id: setup
action: run
provides:
  - chronyd.init
requires:
  - base.init
jobs:
  - RUN: dnf -y install chrony crudini
  - RUN: systemctl start chronyd
  - RUN: systemctl enable chronyd
"""

DUMMY_ANSIBLE_RUNNER_TASK_DATA = """
id: ansible
provides:
  - ansible_task
requires:
  - something
playbook: foo.yml
working_dir: /working/dir
"""


class TestTaskManager(unittest.TestCase):
    """Test TaskManager object"""

    def test_get_instance(self):
        """test instance"""
        obj = tasks.TaskManager.instance()
        self.assertEqual(tasks.TaskManager._instance, obj)
        self.assertRaises(RuntimeError, tasks.TaskManager)

    def test_get_driver(self):
        """test stevedore driver"""
        obj = tasks.TaskManager.instance()
        self.assertTrue(obj.get_driver("service"), tasks.ServiceTask)
        self.assertTrue(obj.get_driver("directord"), tasks.DirectordTask)
        self.assertTrue(obj.get_driver("print"), tasks.PrintTask)
        self.assertRaises(stevedore.exception.NoMatches, obj.get_driver, "doesnotexist")


class TestServiceTask(unittest.TestCase):
    """test ServiceTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_SERVICE_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.ServiceTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "run")
        self.assertEqual(obj.action, "run")
        self.assertEqual(obj.jobs, [{"echo": "service a run"}])

    @mock.patch("time.sleep")
    def test_execute(self, mock_sleep):
        """test execute"""
        obj = tasks.ServiceTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)
        self.assertEqual(str(result), "[{'status': True, 'data': {}}]")

    @mock.patch("time.sleep")
    def test_execute_bad_job(self, mock_sleep):
        """test execute with bad job definition"""
        self.data["jobs"] = [{"bad": "job"}]
        obj = tasks.ServiceTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)


class TestDirectordTask(unittest.TestCase):
    """test DirectordTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_DIRECTORD_SERVICE_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "setup")
        self.assertEqual(obj.action, "run")
        self.assertEqual(obj.jobs, self.data["jobs"])

    @mock.patch("directord.mixin.Mixin")
    def test_execute(self, mock_mixin):
        """test execute"""
        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)

    @mock.patch("directord.user.Manage")
    @mock.patch("directord.mixin.Mixin")
    def test_execute_failure(self, mock_mixin, mock_manage):
        """test execute fails"""
        mixin_obj = mock.MagicMock()
        manage_obj = mock.MagicMock()
        mock_mixin.return_value = mixin_obj
        mock_manage.return_value = manage_obj
        mixin_obj.exec_orchestrations.return_value = [b"foo"]
        manage_obj.poll_job.return_value = (False, "meh")
        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        self.assertRaises(ExecutionFailed, obj.execute)
        mixin_obj.exec_orchestrations.assert_called_once_with(
            [{"jobs": self.data.get("jobs")}],
            defined_targets=["host-a", "host-b"],
            return_raw=True,
        )
        manage_obj.poll_job.assert_called_once_with(job_id="foo")

    @mock.patch("directord.user.Manage")
    @mock.patch("directord.mixin.Mixin")
    def test_execute_exception(self, mock_mixin, mock_manage):
        """test execute throws exception"""
        mixin_obj = mock.MagicMock()
        mock_mixin.return_value = mixin_obj
        mixin_obj.exec_orchestrations.side_effect = Exception("fail")
        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        self.assertRaises(Exception, obj.execute)


class TestPrintTask(unittest.TestCase):
    """test PrintTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_PRINT_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.PrintTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "print")
        self.assertEqual(obj.message, "message from service a")

    def test_execute(self):
        """test execute"""
        obj = tasks.PrintTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)
        self.assertEqual(result[0].data, {})


class TestAnsibleRunnerTask(unittest.TestCase):
    """test AnsibleRunnerTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_ANSIBLE_RUNNER_TASK_DATA)
        runner_patcher = mock.patch("ansible_runner.run")
        self.mock_run = runner_patcher.start()
        self.addCleanup(runner_patcher.stop)

    def test_object(self):
        """test object"""
        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "ansible")
        self.assertEqual(obj.playbook, "foo.yml")
        self.assertEqual(obj.working_dir, "/working/dir")

    def test_execute(self):
        """test execute"""
        mock_result = mock.MagicMock()
        self.mock_run.return_value = mock_result

        mock_result.rc = 0
        mock_result.status = "successful"
        mock_result.stdout = "foo"
        mock_result.stats = {}

        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        result = obj.execute()
        self.assertTrue(result[0].status)
        self.assertEqual(result[0].data, {"stdout": "foo", "stats": {}})

    def test_execute_failure(self):
        """test execute failure"""
        mock_result = mock.MagicMock()
        self.mock_run.return_value = mock_result

        mock_result.rc = 2
        mock_result.status = "successful"
        mock_result.stdout = "foo"
        mock_result.stats = {}

        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        result = obj.execute()
        self.assertFalse(result[0].status)
        self.assertEqual(result[0].data, {"stdout": "foo", "stats": {}})

        mock_result.rc = 0
        mock_result.status = "failed"
        mock_result.stdout = "foo"
        mock_result.stats = {}

        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        result = obj.execute()
        self.assertFalse(result[0].status)
        self.assertEqual(result[0].data, {"stdout": "foo", "stats": {}})
