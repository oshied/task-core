#!/usr/bin/env python3
"""service and task objects"""
import logging
import random
import time
from stevedore import driver

from director import mixin
from director import user
from taskflow import task


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

    def get_driver(self, name) -> task.Task:
        if name not in self._types:
            self._types[name] = driver.DriverManager(
                "task_core.task.types", name=name, invoke_on_load=False
            )
        return self._types[name].driver


class ServiceTask(task.Task):
    """task related to a service"""

    def __init__(self, service: str, data: dict, hosts: list):
        self._service = service
        self._data = data
        self._hosts = hosts
        name = f"{service}-{data.get('id')}"
        provides = data.get("provides", [])
        requires = data.get("requires", [])
        LOG.info("Creating %s: provides: %s, requires: %s", name, provides, requires)
        super().__init__(name=name, provides=provides, requires=requires)

    @property
    def data(self) -> dict:
        return self._data

    @property
    def hosts(self) -> list:
        return self._hosts

    @property
    def service(self) -> str:
        return self._service

    @property
    def task_id(self) -> str:
        return self._data.get("id")

    @property
    def action(self) -> str:
        return self._data.get("action")

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
        return [True]


class DirectorServiceTask(ServiceTask):
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

        jobs = _mixin.exec_orchestrations(
            user_exec=user.User(args=self.DirectorArgs),
            orchestrations=self.jobs,
            defined_targets=self.hosts,
            raw_return=True,
        )

        LOG.error(jobs)

        success = True
        for item in [i.decode() for i in jobs]:
            status, info = _mixin.poll_job(job_id=item)
            if not status:
                # TODO(mwhahaha): handle failures
                LOG.error(info)
                success = False
        return success


class PrintTask(ServiceTask):
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
        return [True]
