#!/usr/bin/env python3
"""inventory and role objects"""
import logging
import yaml


LOG = logging.getLogger(__name__)


class Inventory:
    """service representation"""

    def __init__(self, definition):
        self._data = None
        with open(definition) as fin:
            self._data = yaml.safe_load(fin.read())

    @property
    def data(self) -> dict:
        return self._data

    @property
    def hosts(self) -> dict:
        return self._data.get("hosts", {})

    def get_role_hosts(self, role=None) -> list:
        if role is None:
            return self.hosts.keys()
        return [x for x in self.hosts if role in self.hosts[x].get("role", None)]


class Roles:
    """roles definition"""

    def __init__(self, definition):
        self._roles = {}
        with open(definition) as fin:
            self._data = yaml.safe_load(fin.read())

        for role in self.data.keys():
            self._roles[role] = Role(role, self.data.get(role).get("services", []))

    @property
    def data(self) -> dict:
        return self._data

    @property
    def roles(self) -> dict:
        return self._roles

    def get_services(self, role) -> list:
        return self.roles.get(role).services


class Role:
    """role definition"""
    def __init__(self, name, services):
        self._name = name
        self._services = services

    @property
    def name(self) -> str:
        return self._name

    @property
    def services(self) -> list:
        return self._services
