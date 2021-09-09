#!/usr/bin/env python3
"""service and task objects"""
import logging
import os
import random
import time

try:
    import ansible_runner
except ImportError:
    ansible_runner = None
from stevedore import driver

try:
    from directord import DirectordConnect
except ImportError:
    DirectorConnect = None  # pylint: disable=invalid-name

from .base import BaseTask
from .base import BaseInstance
from .exceptions import ExecutionFailed

LOG = logging.getLogger(__name__)


class TaskManager(BaseInstance):
    """task type loader"""

    _instance = None
    _types = {}

    def get_driver(self, name) -> BaseTask:
        if name not in self._types:
            self._types[name] = driver.DriverManager(
                "task_core.task.types", name=name, invoke_on_load=False
            )
        return self._types[name].driver


class TaskResult:
    """task result object"""

    def __init__(self, status: bool, data: dict):
        self._status = status
        self._data = data

    @property
    def status(self) -> bool:
        """task result status"""
        return self._status

    @property
    def data(self) -> dict:
        """rturn data info"""
        return self._data

    def __repr__(self):
        return repr({"status": self.status, "data": self.data})


class ServiceTask(BaseTask):
    """task related to a service"""

    @property
    def jobs(self) -> list:
        return self._data.get("jobs", [])

    def execute(self, *args, **kwargs) -> list:
        LOG.debug(
            "%s | task execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            self,
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("%s | Running", self)
        for j in self.jobs:
            if "echo" in j:
                LOG.info(j.get("echo"))
                time.sleep(random.random())
            else:
                LOG.info("%s | Unknown action: %s", self, j)
        # note: this return time needs to match the "provides" format type.
        # generally a list or dict
        LOG.info("%s | Completed", self)
        return [TaskResult(True, {})]


class DirectordTask(ServiceTask):
    """Service task posting to directord.

    https://directord.com/library.html

    Execute a set of jobs against a directord cluster. Execution returns a
    byte encoded list of jobs UUID.

    :returns: List
    """

    def execute(self, *args, **kwargs) -> list:
        if not DirectordConnect():
            raise Exception(
                "directord libraries are unavailable. Please install directord."
            )
        LOG.debug(
            "%s directord execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            self,
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("%s | Running", self)

        # TODO(mwhahaha): make this configurable @ task level
        conn = DirectordConnect(
            force_async=True  # pylint: disable=unexpected-keyword-arg
        )

        try:
            jobs = conn.orchestrate(
                orchestrations=[{"jobs": self.jobs}],
                defined_targets=self.hosts,
            )
        except Exception as e:
            LOG.error("%s | Exception while executing orcestrations, %s", self, e)
            raise

        LOG.debug("%s | Pending jobs... %s", self, jobs)

        pending = jobs
        success = []
        failure = []
        while len(pending) > 0:
            job = pending.pop(0)
            LOG.debug("%s | Waiting for job... %s", self, job)
            status, info = conn.poll(job_id=job)
            if status is True:
                success.append(job)
            elif status is False:
                # TODO(mwhahaha): handle failures
                LOG.error("%s | Job %s failed. %s", self, job, info)
                failure.append(job)
            else:
                pending.append(job)
                time.sleep(0.1)

        LOG.info("%s | Finished processing", self)
        # TODO(mwhahaha): I don't think we need to stop execution here
        if failure:
            raise ExecutionFailed(
                "{} | Directord job execution failed {}".format(
                    self, ", ".join(failure)
                )
            )

        results = dict(success=success, failure=failure)
        return [TaskResult(not any(failure), results)]


class PrintTask(BaseTask):
    """Task that just prints itself out"""

    @property
    def message(self):
        return self.data.get("message")

    def execute(self, *args, **kwargs) -> list:
        LOG.debug(
            "%s print execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            self,
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("%s | Running", self)
        LOG.info("PRINT: %s", self.message)
        LOG.info("%s | Completed", self)
        return [TaskResult(True, {})]


class AnsibleRunnerTask(BaseTask):
    """ansible task"""

    @property
    def playbook(self) -> str:
        return self._data.get("playbook")

    @property
    def inventory(self) -> str:
        return self._data.get("inventory")

    @property
    def working_dir(self) -> str:
        return self._data.get("working_dir", os.getcwd())

    def execute(self, *args, **kwargs) -> list:
        if not ansible_runner:
            raise Exception(
                "ansible-runner libraries are unavailable. Please "
                "install ansible-runner."
            )
        LOG.debug(
            "%s ansible execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            self,
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("%s | Running", self)
        runner = ansible_runner.run(
            private_data_dir=self.working_dir,
            playbook=self.playbook,
            inventory=self.inventory,
        )
        data = {"stdout": runner.stdout, "stats": runner.stats}
        # https://ansible-runner.readthedocs.io/en/stable/python_interface.html#the-runner-object
        status = runner.rc == 0 and runner.status == "successful"
        LOG.info("%s | Completed", self)
        return [TaskResult(status, data)]
