#!/usr/bin/env python3
"""schema classess"""
import logging
import os
import sys
import jsonschema
import yaml
from .base import BaseInstance

LOG = logging.getLogger(__name__)


class BaseSchemaValidator(BaseInstance):
    """base schema validator"""

    _instance = None
    _schema = None
    _schema_path = None

    @property
    def schema_folder(self):
        if self._schema_path:
            return self._schema_path
        prefixes = [
            # venv
            os.path.join(sys.prefix, "share", "task-core"),
            # rpm
            os.path.join("/usr", "share", "task-core"),
            # sudo pip
            os.path.join("/usr", "local", "share", "task-core"),
        ]
        for prefix in prefixes:
            schema_path = os.path.join(prefix, "schema")
            if os.path.exists(schema_path):
                LOG.debug("Found schema path %s", schema_path)
                self._schema_path = schema_path
                break
        return self._schema_path

    @property
    def schema(self):
        raise NotImplementedError("Please implement schema to return the schema")

    def _load_schema(self, filename):
        with open(
            os.path.join(self.schema_folder, filename), encoding="utf-8", mode="r"
        ) as schema_file:
            self._schema = yaml.safe_load(schema_file.read())

    def validate(self, obj):
        return jsonschema.validate(obj, self.schema)


class InventorySchemaValidator(BaseSchemaValidator):
    """inventory file validator"""

    _instance = None
    _schema = None

    @property
    def schema(self):
        if self._schema is None:
            self._load_schema("inventory.yaml")
        return self._schema


class RolesSchemaValidator(BaseSchemaValidator):
    """roles file validator"""

    _instance = None
    _schema = None

    @property
    def schema(self):
        if self._schema is None:
            self._load_schema("roles.yaml")
        return self._schema


class ServiceSchemaValidator(BaseSchemaValidator):
    """service file validator"""

    _instance = None
    _schema = None

    @property
    def schema(self):
        if self._schema is None:
            self._load_schema("service.yaml")
        return self._schema
