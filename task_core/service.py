#!/usr/bin/env python3
"""service and task objects"""
import logging
import yaml
from .base import BaseFileData
from .tasks import TaskManager
from .schema import ServiceSchemaValidator


LOG = logging.getLogger(__name__)


class Service(BaseFileData):
    """service representation"""

    def __init__(self, definition):
        self._data = None
        self._tasks = None
        self._hosts = []
        super().__init__(definition)
        ServiceSchemaValidator.instance().validate(self._data)
        self._task_mgr = TaskManager.instance()

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

    def get_tasks_needed_by(self):
        """build a dict of needed by and provides"""
        refs = {}
        for _task in self.tasks:
            provides = _task.get("provides", [])
            for need in _task.get("needed-by", []):
                if refs.get(need):
                    refs[need] = sorted(list(set(refs[need] + provides)))
                else:
                    refs[need] = sorted(list(set(provides)))
        return refs

    def update_task_requires(self, needs: dict):
        """update task requires based on needed by info"""
        for _task in self.tasks:
            for need, provides in needs.items():
                if provides is None:
                    # shouldn't be None, but to be safe let's skip it
                    LOG.warning("A task with no provides has a needed-by %s", need)
                    continue
                if provides is not None and isinstance(provides, str):
                    provides = [provides]
                if need in _task.get("provides", []):
                    _task["requires"] = list(set(_task.get("requires", []) + provides))

    def build_tasks(self, task_type_override=None):
        tasks = []
        for _task in self.tasks:
            if task_type_override:
                task_type = task_type_override
            else:
                task_type = self._task_mgr.get_driver(_task.get("driver", "service"))
            task = task_type(self.name, _task, self.hosts)
            task.version = tuple(int(v) for v in self.version.split("."))
            tasks.append(task)
        return tasks

    def save(self, location) -> None:
        with open(location, encoding="utf-8", mode="w") as fout:
            yaml.dump(self.data, fout)
