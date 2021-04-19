#!/usr/bin/env python3
"""service and task objects"""
import logging
import random
import time
import yaml
from taskflow import task


LOG = logging.getLogger(__name__)


class Service:
    """service representation"""

    def __init__(self, definition):
        self._data = None
        self._tasks = None
        self._hosts = []
        with open(definition) as fin:
            self._data = yaml.safe_load(fin.read())

    @property
    def data(self) -> dict:
        return self._data

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
    def name(self) -> str:
        return self._data.get("id")

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
        if not self._tasks:
            task_data = self._data.get("tasks", [])
            self._tasks = []
            for _task in task_data:
                self._tasks.append(ServiceTask(self.name, _task, self._hosts))
        return self._tasks

    def save(self, location) -> None:
        with open(location, "w") as fout:
            yaml.dump(self.data, fout)


class ServiceTask(task.Task):
    """task related to a service"""

    def __init__(self, service: str, data: dict, hosts: list):
        self._service = service
        self._data = data
        self._hosts = hosts
        name = f"{service}-{data.get('id')}"
        provides = data.get("provides", [])
        requires = data.get("requires", [])
        LOG.info(f"Creating {name}: provides: {provides}, requires: {requires}")
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

    def execute(self, *args, **kwargs) -> bool:
        LOG.info(f"task execute: {args}, {kwargs}, hosts: {self.hosts}, data; {self.data}")
        for j in self.jobs:
            if "echo" in j:
                LOG.info(j.get("echo"))
                time.sleep(random.random())
            else:
                LOG.info(f"Unsupported action: {j}")
                return [False]
        # note: this return time needs to match the "provides" format type.
        # generally a list or dict
        return [True]
