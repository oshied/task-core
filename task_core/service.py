#!/usr/bin/env python3
"""service and task objects"""
import logging
import yaml
from task_core.base import BaseFileData
from task_core.tasks import ServiceTask


LOG = logging.getLogger(__name__)


class Service(BaseFileData):
    """service representation"""

    def __init__(self, definition):
        self._data = None
        self._tasks = None
        self._hosts = []
        super().__init__(definition)

    @property
    def hosts(self) -> list:
        return self._hosts

    def add_host(self, host) -> list:
        self._hosts.append(host)
        return self.hosts

    def remove_host(self, host) -> list:
        self._hosts.remove(host)
        return self.hosts

    @property
    def type(self) -> str:
        return self._data.get("type", "service")

    @property
    def version(self) -> str:
        return self._data.get("version")

    @property
    def provides(self):
        return self.name

    @property
    def requires(self) -> list:
        return self._data.get("requires", [])

    @property
    def tasks(self) -> list:
        return self._data.get("tasks", [])

    def build_tasks(self, task_type=ServiceTask):
        tasks = []
        for _task in self.tasks:
            tasks.append(task_type(self.name, _task, self.hosts))
        return tasks

    def save(self, location) -> None:
        with open(location, "w") as fout:
            yaml.dump(self.data, fout)
