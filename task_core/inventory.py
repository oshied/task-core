#!/usr/bin/env python3
"""inventory and role objects"""
from task_core.base import BaseFileData


class Inventory(BaseFileData):
    """service representation"""
    @property
    def hosts(self) -> dict:
        return self._data.get("hosts", {})

    def get_role_hosts(self, role=None) -> list:
        if role is None:
            return self.hosts.keys()
        return [x for x in self.hosts if role in self.hosts[x].get("role", None)]


class Roles(BaseFileData):
    """roles definition"""
    def __init__(self, definition):
        self._roles = {}
        super().__init__(definition)
        for role in self.data.keys():
            self._roles[role] = Role(role, self.data.get(role).get("services", []))

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
