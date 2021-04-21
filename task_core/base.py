#!/usr/bin/env python3
"""base classess"""
import yaml
from taskflow import task


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
