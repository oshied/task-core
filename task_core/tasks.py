#!/usr/bin/env python3
"""service and task objects"""
import logging
import os
import random
import time

import ansible_runner
from stevedore import driver
from directord import DirectordConnect

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
            "task execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("Running %s", self)
        for j in self.jobs:
            if "echo" in j:
                LOG.info(j.get("echo"))
                time.sleep(random.random())
            else:
                LOG.info("Unknown action: %s", j)
        # note: this return time needs to match the "provides" format type.
        # generally a list or dict
        LOG.info("Completed %s", self)
        return [TaskResult(True, {})]


class DirectordTask(ServiceTask):
    """Service task posting to directord.

    https://directord.com/library.html

    Execute a set of jobs against a directord cluster. Execution returns a
    byte encoded list of jobs UUID.

    :returns: List
    """

    def execute(self, *args, **kwargs) -> list:
        LOG.debug(
            "task execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("Running %s", self)

        conn = DirectordConnect()

        try:
            jobs = conn.orchestrate(
                orchestrations=[{"jobs": self.jobs}],
                defined_targets=self.hosts,
            )
        except Exception as e:
            LOG.error("Exception while executing orcestrations, %s", e)
            raise

        LOG.debug(jobs)

        failure = list()
        for item in jobs:
            LOG.debug("Waiting for job... %s", item)
            status, info = conn.poll(job_id=item)
            if status is False:
                # TODO(mwhahaha): handle failures
                LOG.error(info)
                failure.append(item)

        if failure:
            raise ExecutionFailed("Directord job execution failed")

        LOG.info("Completed %s", self)
        return [TaskResult(not any(failure), {})]


class PrintTask(BaseTask):
    """Task that just prints itself out"""

    @property
    def message(self):
        return self.data.get("message")

    def execute(self, *args, **kwargs) -> list:
        LOG.debug(
            "task execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("Running %s", self)
        LOG.info("PRINT: %s", self.message)
        LOG.info("Completed %s", self)
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
        LOG.debug(
            "ansible execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            args,
            kwargs,
            self.hosts,
            self.data,
        )
        LOG.info("Running %s", self)
        runner = ansible_runner.run(
            private_data_dir=self.working_dir,
            playbook=self.playbook,
            inventory=self.inventory,
        )
        data = {"stdout": runner.stdout, "stats": runner.stats}
        # https://ansible-runner.readthedocs.io/en/stable/python_interface.html#the-runner-object
        status = runner.rc == 0 and runner.status == "successful"
        LOG.info("Completed %s", self)
        return [TaskResult(status, data)]
