#!/usr/bin/env python3
"""base classess"""
import logging
import yaml
from taskflow import task

LOG = logging.getLogger(__name__)


class BaseFileData:
    """base object from file"""

    def __init__(self, definition):
        self._data = None
        with open(definition) as fin:
            self._data = yaml.safe_load(fin.read())

    @property
    def data(self) -> dict:
        return self._data

    @property
    def name(self) -> str:
        return self._data.get("id", self._data.get("name"))


class BaseTask(task.Task):
    """base task"""

    def __init__(self, service: str, data: dict, hosts: list):
        self._service = service
        self._data = data
        self._hosts = hosts
        name = f"{service}-{data.get('id')}"
        provides = data.get("provides", [])
        requires = data.get("requires", [])
        LOG.debug("Creating %s: provides: %s, requires: %s", name, provides, requires)
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

    def execute(self, *args, **kwargs):
        raise NotImplementedError("Execute function needs to be implemented")


class BaseInstance:  # pylint: disable=too-few-public-methods
    """Base instance class"""

    _instance = None

    def __init__(self):
        raise RuntimeError("Use instance()")

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance
