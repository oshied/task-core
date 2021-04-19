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
        with open(definition) as fin:
            self._data = yaml.safe_load(fin.read())

    @property
    def data(self) -> dict:
        return self._data

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        return self._data.get("id")

    @property
    def type(self) -> str:
        return self._data.get("type", "service")

    @property
    def version(self) -> str:
        return self._data.get("version")

    @property
    def provides(self):
        return self.id

    @property
    def requires(self) -> list:
        return self._data.get("requires", [])

    @property
    def tasks(self) -> list:
        if not self._tasks:
            task_data = self._data.get("tasks", [])
            self._tasks = []
            for _task in task_data:
                self._tasks.append(ServiceTask(self.id, _task))
        return self._tasks

    def save(self, location) -> None:
        with open(location, "w") as fout:
            yaml.dump(self.data, fout)


class ServiceTask(task.Task):
    """task related to a service"""

    def __init__(self, service: str, data: dict):
        self._service = service
        self._data = data
        name = f"{service}-{data.get('id')}"
        provides = data.get("provides", [])
        requires = data.get("requires", [])
        LOG.info(f"Creating {name}: provides: {provides}, requires: {requires}")
        super().__init__(name=name, provides=provides, requires=requires)

    @property
    def data(self) -> dict:
        return self._data

    @property
    def service(self) -> str:
        return self._service

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        return self._data.get("id")

    @property
    def action(self) -> str:
        return self._data.get("action")

    @property
    def jobs(self) -> list:
        return self._data.get("jobs", [])

    def execute(self, *args, **kwargs) -> bool:
        LOG.info(f"task execute: {args}, {kwargs}, data; {self.data}")
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
