# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""unit tests of tasks"""
import subprocess
import stevedore.exception
import unittest
import yaml
from unittest import mock
from task_core import tasks
from task_core.exceptions import ExecutionFailed

try:
    import ansible_runner

    ANSIBLE_RUNNER_UNAVAILABLE = False
except:
    ANSIBLE_RUNNER_UNAVAILABLE = True

try:
    import directord

    DIRECTORD_UNAVAILABLE = False
except:
    DIRECTORD_UNAVAILABLE = True


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

DUMMY_LOCAL_TASK_DATA = """
id: local
provides:
  - local
requires:
  - local
command: >
  sleep 10
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


@unittest.skipIf(DIRECTORD_UNAVAILABLE, "directord library unavailable")
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

    @mock.patch("task_core.tasks.DirectordConnect")
    def test_execute(self, mock_client):
        """test execute"""
        mock_conn = mock.MagicMock()
        mock_conn.orchestrate.return_value = []
        mock_client.return_value = mock_conn
        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)

    @mock.patch("task_core.tasks.DirectordConnect")
    def test_execute_success(self, mock_client):
        """test execute"""
        mock_conn = mock.MagicMock()
        mock_poll = mock.MagicMock()
        mock_conn.orchestrate.return_value = ["foo"]
        mock_client.return_value = mock_conn
        mock_conn.poll = mock_poll
        mock_poll.return_value = (True, "yay")

        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)

    @mock.patch("task_core.tasks.DirectordConnect")
    def test_execute_failure(self, mock_client):
        """test execute fails"""
        mock_conn = mock.MagicMock()
        mock_poll = mock.MagicMock()
        mock_conn.orchestrate.return_value = ["foo"]
        mock_client.return_value = mock_conn
        mock_conn.poll = mock_poll
        mock_poll.return_value = (False, "meh")

        obj = tasks.DirectordTask("foo", self.data, ["host-a", "host-b"])
        self.assertRaises(ExecutionFailed, obj.execute)
        mock_conn.orchestrate.assert_called_once_with(
            orchestrations=[{"jobs": self.data.get("jobs")}],
            defined_targets=["host-a", "host-b"],
        )
        mock_poll.assert_called_once_with(job_id="foo")

    @mock.patch("task_core.tasks.DirectordConnect")
    def test_execute_exception(self, mock_client):
        """test execute throws exception"""
        mock_conn = mock.MagicMock()
        mock_conn.orchestrate.return_value = []
        mock_client.side_effect = Exception("fail")
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


@unittest.skipIf(ANSIBLE_RUNNER_UNAVAILABLE, "ansible runner library unavailable")
class TestAnsibleRunnerTask(unittest.TestCase):
    """test AnsibleRunnerTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_ANSIBLE_RUNNER_TASK_DATA)
        runner_cfg_patcher = mock.patch("ansible_runner.runner_config.RunnerConfig")
        self.mock_run_cfg = runner_cfg_patcher.start()
        self.addCleanup(runner_cfg_patcher.stop)
        runner_patcher = mock.patch("ansible_runner.Runner")
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

    def test_object_paths(self):
        """test ansible paths"""
        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        env = obj._default_ansible_paths()
        expected = {
            "ANSIBLE_ACTION_PLUGINS": (
                "/working/dir/action:/usr/share/ansible/plugins/action"
            ),
            "ANSIBLE_CALLBACK_PLUGINS": (
                "/working/dir/callback:/usr/share/ansible/plugins/callback"
            ),
            "ANSIBLE_FILTER_PLUGINS": (
                "/working/dir/filter:/usr/share/ansible/plugins/filter"
            ),
            "ANSIBLE_LIBRARY": (
                "/working/dir/modules:/usr/share/ansible/plugins/modules"
            ),
            "ANSIBLE_LOOKUP_PLUGINS": (
                "/working/dir/lookup:/usr/share/ansible/plugins/lookup"
            ),
            "ANSIBLE_ROLES_PATH": (
                "/working/dir/roles:/usr/share/ansible/roles:/etc/ansible/roles"
            ),
        }
        self.assertEqual(env, expected)

    def test_execute(self):
        """test execute"""
        mock_result = mock.MagicMock()
        self.mock_run.return_value = mock_result

        mock_result.run.return_value = ("successful", 0)
        self.mock_run.return_value.stdout = "foo"
        self.mock_run.return_value.stats = {}

        mock_paths = mock.MagicMock()
        mock_paths.return_value = {}
        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        obj._default_ansible_paths = mock_paths
        result = obj.execute()
        self.assertTrue(result[0].status)
        self.assertEqual(result[0].data, {"stdout": "foo", "stats": {}})
        self.mock_run_cfg.assert_called_once_with(
            envvars={},
            playbook="foo.yml",
            private_data_dir="/working/dir",
            project_dir="/working/dir",
        )
        self.mock_run.assert_called_once_with(config=self.mock_run_cfg.return_value)

        self.mock_run_cfg.reset_mock()
        self.mock_run.reset_mock()
        with mock.patch("os.path.exists", return_value=True):
            result = obj.execute()
            self.mock_run_cfg.assert_called_once_with(
                envvars={"ANSIBLE_CONFIG": "/working/dir/ansible.cfg"},
                inventory="/working/dir/inventory.yaml",
                playbook="foo.yml",
                private_data_dir="/working/dir",
                project_dir="/working/dir",
            )

    def test_execute_failure(self):
        """test execute failure"""
        mock_result = mock.MagicMock()
        self.mock_run.return_value = mock_result

        mock_result = mock.MagicMock()
        self.mock_run.return_value = mock_result

        mock_result.run.return_value = ("successful", 2)
        self.mock_run.return_value.stdout = "foo"
        self.mock_run.return_value.stats = {}

        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        self.assertRaises(ExecutionFailed, obj.execute)

        mock_result.run.return_value = ("failed", 0)
        self.mock_run.return_value.stdout = "foo"
        self.mock_run.return_value.stats = {}

        obj = tasks.AnsibleRunnerTask("foo", self.data, ["host-a"])
        self.assertRaises(ExecutionFailed, obj.execute)


class TestNoopTask(unittest.TestCase):
    """test NoopTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_PRINT_TASK_DATA)

    def test_object(self):
        """test basic object"""
        obj = tasks.NoopTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.service, "foo")
        self.assertEqual(obj.task_id, "print")

    def test_execute(self):
        """test execute"""
        obj = tasks.NoopTask("foo", self.data, ["host-a", "host-b"])
        result = obj.execute()
        self.assertTrue(result[0].status)
        self.assertEqual(result[0].data, {"hosts": ["host-a", "host-b"], "id": "print"})


class TestLocalTask(unittest.TestCase):
    """test LocalTask"""

    def setUp(self):
        super().setUp()
        self.data = yaml.safe_load(DUMMY_LOCAL_TASK_DATA)
        popen_patcher = mock.patch("subprocess.Popen")
        self.mock_popen = popen_patcher.start()
        self.addCleanup(popen_patcher.stop)

    def test_object(self):
        """test basic object"""
        obj = tasks.LocalTask("foo", self.data, ["host-a", "host-b"])
        self.assertEqual(obj.data, self.data)
        self.assertEqual(obj.hosts, ["host-a", "host-b"])
        self.assertEqual(obj.command, "sleep 10\n")
        self.assertEqual(obj.quiet, False)
        self.assertEqual(obj.returncodes, [0])

    def test_execute(self):
        """test execute"""
        obj = tasks.LocalTask("foo", self.data, ["host-a", "host-b"])
        mock_proc = self.mock_popen.return_value.__enter__()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.side_effect = [b"output", StopIteration()]
        result = obj.execute()
        self.mock_popen.assert_called_once_with(
            "sleep 10",
            shell=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        self.assertTrue(result[0].status)
        self.assertEqual(
            result[0].data, {"id": "local", "command": "sleep 10", "returncode": 0}
        )

        self.mock_popen.reset_mock()
        mock_proc.reset_mock()
        mock_proc.stdout.readline.side_effect = [b"output", b""]
        result = obj.execute()
        self.mock_popen.assert_called_once_with(
            "sleep 10",
            shell=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )

        self.assertTrue(result[0].status)
        self.assertEqual(
            result[0].data, {"id": "local", "command": "sleep 10", "returncode": 0}
        )

    def test_execute_quiet(self):
        """test execute quiet"""
        obj = tasks.LocalTask("foo", self.data, ["host-a", "host-b"])
        mock_proc = self.mock_popen.return_value.__enter__()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"output", b"")
        obj.data["quiet"] = True
        result = obj.execute()
        self.mock_popen.assert_called_once_with(
            "sleep 10",
            shell=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )

        self.assertTrue(result[0].status)
        self.assertEqual(
            result[0].data,
            {
                "id": "local",
                "command": "sleep 10",
                "output": b"output",
                "errors": b"",
                "returncode": 0,
            },
        )

    def test_execute_return_codes(self):
        """test execute return codes"""
        obj = tasks.LocalTask("foo", self.data, ["host-a", "host-b"])
        mock_proc = self.mock_popen.return_value.__enter__()
        mock_proc.returncode = 2
        mock_proc.stdout.readline.side_effect = [b"output", StopIteration()]
        obj.data["returncodes"] = [0, 2]
        result = obj.execute()
        self.mock_popen.assert_called_once_with(
            "sleep 10",
            shell=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )

        self.assertTrue(result[0].status)
        self.assertEqual(
            result[0].data,
            {
                "id": "local",
                "command": "sleep 10",
                "returncode": 2,
            },
        )

        self.mock_popen.reset_mock()
        mock_proc.reset_mock()
        mock_proc.returncode = 5
        result = obj.execute()
        self.assertFalse(result[0].status)
        self.assertEqual(
            result[0].data,
            {
                "id": "local",
                "command": "sleep 10",
                "returncode": 5,
            },
        )
