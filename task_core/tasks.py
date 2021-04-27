#!/usr/bin/env python3
"""service and task objects"""
import logging
import os
import random
import time

import ansible_runner
from stevedore import driver
from director import mixin
from director import user

from .base import BaseTask
from .exceptions import ExecutionFailed

LOG = logging.getLogger(__name__)


class TaskManager:
    """task type loader"""

    _instance = None
    _types = {}

    def __init__(self):
        raise RuntimeError("Use instance()")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

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
        for j in self.jobs:
            if "echo" in j:
                LOG.info(j.get("echo"))
                time.sleep(random.random())
            else:
                LOG.info("Unknown action: %s", j)
        # note: this return time needs to match the "provides" format type.
        # generally a list or dict
        return [TaskResult(True, {})]


class DirectorTask(ServiceTask):
    """Service task posting to director.

    https://cloudnull.github.io/director/orchestrations.html#orchestration-library-usage

    Execute a set of jobs against a director cluster. Execution returns a
    byte encoded list of jobs UUID.

    :returns: List
    """

    class DirectorArgs:  # pylint: disable=too-few-public-methods
        """Arguments required to interface with Director."""

        debug = False
        socket_path = "/var/run/director.sock"
        mode = "orchestrate"

    def execute(self, *args, **kwargs) -> list:
        LOG.debug(
            "task execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            args,
            kwargs,
            self.hosts,
            self.data,
        )

        _mixin = mixin.Mixin(args=self.DirectorArgs)
        _user = user.Manage(args=self.DirectorArgs)

        try:
            jobs = _mixin.exec_orchestrations(
                user_exec=_user,
                orchestrations=self.jobs,
                defined_targets=self.hosts,
                return_raw=True,
            )
        except Exception as e:
            LOG.error("Exception while executing orcestrations, %s", e)
            raise

        LOG.debug(jobs)

        success = True
        for item in [i.decode() for i in jobs]:
            LOG.debug("Waiting for job... %s", item)
            status, info = _user.poll_job(job_id=item)
            if not status:
                # TODO(mwhahaha): handle failures
                LOG.error(info)
                success = False
        if not success:
            raise ExecutionFailed("Director job execution failed")
        return [TaskResult(success, {})]


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
        LOG.info("PRINT: %s", self.message)
        return [TaskResult(True, {})]


class AnsibleRunnerTask(BaseTask):
    """ansible task"""

    @property
    def playbook(self) -> str:
        return self._data.get("playbook")

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
        runner = ansible_runner.run(
            private_data_dir=self.working_dir, playbook=self.playbook
        )
        data = {"stdout": runner.stdout, "stats": runner.stats}
        # https://ansible-runner.readthedocs.io/en/stable/python_interface.html#the-runner-object
        status = runner.rc == 0 and runner.status == "successful"
        return [TaskResult(status, data)]
