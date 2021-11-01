# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""inventory and role objects"""
from .exceptions import InvalidRole
from .base import BaseFileData
from .schema import InventorySchemaValidator
from .schema import RolesSchemaValidator


class Inventory(BaseFileData):
    """service representation"""

    def __init__(self, definition):
        super().__init__(definition)
        InventorySchemaValidator.instance().validate(self._data)

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
        RolesSchemaValidator.instance().validate(self._data)
        for role in self.data.keys():
            self._roles[role] = Role(role, self.data.get(role).get("services", []))

    @property
    def roles(self) -> dict:
        return self._roles

    def get_services(self, role) -> list:
        if role not in self.roles:
            raise InvalidRole(f"Role '{role}' is not defined in the roles file")
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
