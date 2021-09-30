#!/usr/bin/env python3
"""base classess"""
import glob
import logging
import os
import yaml
from taskflow import task
from taskflow.types import sets
from .exceptions import InvalidFileData
from .utils import merge_dict

LOG = logging.getLogger(__name__)


class BaseFileData:
    """base object from file"""

    def __init__(self, definition):
        self._data = None
        if os.path.isfile(definition):
            # if we were given a file, load it
            with open(definition, encoding="utf-8", mode="r") as fin:
                self._data = yaml.safe_load(fin)
        elif os.path.isdir(definition):
            # if the definition is a directory, then find all the
            # yaml files in the directory and merge them together
            self._data = {}
            files = glob.glob(os.path.join(definition, "**", "*.y*ml"), recursive=True)
            for file in files:
                with open(file, encoding="utf-8", mode="r") as fin:
                    self._data = merge_dict(self._data, yaml.safe_load(fin))
        elif isinstance(definition, dict):
            self._data = definition
        else:
            raise InvalidFileData(
                "Invalid file data provided. definition "
                "should be either a file path, a directory "
                "path, or a dict. definition provided was "
                f"{type(definition)}"
            )

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
    def driver(self) -> str:
        return self._data.get("driver")

    @property
    def task_id(self) -> str:
        return self._data.get("id")

    @property
    def action(self) -> str:
        return self._data.get("action")

    @property
    def task_provides(self) -> list:
        return self._data.get("provides")

    @property
    def task_requires(self) -> list:
        return self._data.get("requires", [])

    @property
    def task_needed_by(self) -> list:
        return self._data.get("needed-by", [])

    def update_requires(self, vals: list):
        LOG.debug("Updating %s requires to include %s", self.name, vals)
        self.requires = self.requires.union(sets.OrderedSet(vals))

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
