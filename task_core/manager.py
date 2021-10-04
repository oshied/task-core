#!/usr/bin/env python3
"""task manager"""
import glob
import logging
import os

try:
    import networkx
except ImportError:
    networkx = None

from taskflow import exceptions as tf_exc
from taskflow.patterns import graph_flow as gf

from .exceptions import InvalidService, UnavailableException
from .inventory import Inventory
from .inventory import Roles
from .service import Service

LOG = logging.getLogger(__name__)


class TaskManager:
    """task-core manager"""

    def __init__(
        self,
        services_dir: str,
        inventory_file: str,
        roles_file: str,
        skip_loading: bool = False,
    ):
        """load task maanger data"""
        # validate inputs
        if not os.path.isdir(services_dir):
            raise Exception(f"{services_dir} does not exist or is not a directory")
        if not os.path.isfile(inventory_file):
            raise Exception(f"{inventory_file} does not exist or is not a file")
        if not os.path.isfile(roles_file):
            raise Exception(f"{roles_file} does not exist or is not a file")

        self.services_dir = services_dir
        self.inventory_file = inventory_file
        self.roles_file = roles_file
        self.services = {}
        self.inventory = []
        self.roles = []
        if not skip_loading:
            self.load()

    def load(self):
        # load data
        self.load_services()
        self.load_inventory()
        self.load_roles()
        self.hosts_to_services()

    def load_services(self) -> dict:
        LOG.info("Loading services from %s", self.services_dir)
        files = glob.glob(
            os.path.join(self.services_dir, "**", "*.yaml"), recursive=True
        )
        for file in files:
            try:
                svc = Service(file)
            except Exception:
                LOG.error("Error loading %s", file)
                raise
            self.services[svc.name] = svc
        return self.resolve_service_deps()

    def load_inventory(self) -> dict:
        """load inventory from file"""
        LOG.info("Loading inventory from %s", self.inventory_file)
        self.inventory = Inventory(self.inventory_file)
        return self.inventory

    def load_roles(self) -> dict:
        """load roles from file"""
        LOG.info("Loading roles from %s", self.roles_file)
        self.roles = Roles(self.roles_file)
        return self.roles

    def resolve_service_deps(self) -> dict:
        """loop through services and handle needed_by"""
        LOG.info("Handling extra service dependencies...")
        needed_by = {}
        for name in self.services:
            service = self.services.get(name)
            needs = service.get_tasks_needed_by()
            for need, provides in needs.items():
                needed_by[need] = list(set(needed_by.get(need, []) + provides))
        for name in self.services:
            service = self.services.get(name)
            service.update_task_requires(needed_by)
        return self.services

    def hosts_to_services(self):
        for host in self.inventory.hosts.keys():
            for svc in self.roles.get_services(
                self.inventory.hosts.get(host).get("role")
            ):
                LOG.debug("Adding %s to %s", host, svc)
                try:
                    self.services[svc].add_host(host)
                except KeyError as e:
                    raise InvalidService(f"Service '{svc}' is not defined") from e
        return self.services

    def create_flow(self, task_type_override=None) -> gf.Flow:
        LOG.info("Creating graph flow...")
        flow = gf.Flow("root")
        for service_id in self.services:
            service = self.services.get(service_id)
            if len(service.hosts) == 0:
                # skip services with no target hosts
                LOG.warning(
                    "Skipping adding service %s due to no hosts...", service.name
                )
                continue
            LOG.debug("Adding %s tasks...", service.name)
            try:
                for task in service.build_tasks(task_type_override):
                    flow.add(task)
            except tf_exc.DependencyFailure as fail_exc:
                try:
                    self.write_flow_graph(flow, "failure.svg")
                except UnavailableException:
                    pass
                raise fail_exc
        return flow

    def write_flow_graph(self, flow, output_file="output.svg") -> None:
        if networkx is None:
            raise UnavailableException(
                "networkx is unavailable. Cannot create flow graph"
            )
        dot = networkx.drawing.nx_pydot.to_pydot(
            flow._graph  # pylint: disable=protected-access
        )
        dot.write_svg(output_file)
        LOG.info("Flow graph svg written out to %s", output_file)
