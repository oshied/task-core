#!/usr/bin/env python3
"""service and task objects"""
import logging
import random
import time

from director import mixin
from director import user
from taskflow import task


LOG = logging.getLogger(__name__)


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
        LOG.info(
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

    class DirectorArgs(object):
        """Arguments required to interface with Director."""

        debug=False
        socket_path='/var/run/director.sock'
        mode='orchestrate'

    def execute(self, *args, **kwargs) -> list:
        LOG.info(
            "task execute - args: %s, kwargs: %s, hosts: %s, data; %s",
            args,
            kwargs,
            self.hosts,
            self.data,
        )

        _mixin = mixin.Mixin(args=self.DirectorArgs)

        return _mixin.exec_orchestartions(
            user_exec=user.User(args=self.DirectorArgs),
            orchestrations=self.jobs,
            defined_targets=self.hosts,
            raw_return=True,
        )
