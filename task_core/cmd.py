#!/usr/bin/env python3
"""task-core cli"""
import argparse
import glob
import logging
import os
import pprint
import sys
from datetime import datetime

import networkx

from taskflow import engines
from taskflow import exceptions as tf_exc
from taskflow.patterns import graph_flow as gf

from .exceptions import InvalidService, UnavailableException
from .logging import setup_basic_logging
from .manager import TaskManager
from .service import Service

LOG = logging.getLogger(__name__)


class Cli:
    """task-core cli"""

    def __init__(self):
        self._parser = argparse.ArgumentParser(description="")

    @property
    def parser(self):
        return self._parser

    def parse_args(self):
        self.parser.add_argument(
            "-s",
            "--services-dir",
            required=True,
            help=("Path to a directory containing service definitions"),
        )
        self.parser.add_argument(
            "-i",
            "--inventory-file",
            required=True,
            help=("Path to an inventory file containing hosts to role mappings"),
        )
        self.parser.add_argument(
            "-r",
            "--roles-file",
            required=True,
            help=("Path to a roles file containing roles to service mappings"),
        )
        self.parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            default=False,
            help=("Enable debug logging"),
        )
        self.parser.add_argument(
            "--noop",
            action="store_true",
            default=False,
            help=("Do not run the deployment, only process the tasks"),
        )
        args = self.parser.parse_args()
        return args


def load_services(services_dir) -> dict:
    files = glob.glob(os.path.join(services_dir, "**", "*.yaml"), recursive=True)
    services = {}
    for file in files:
        try:
            svc = Service(file)
        except Exception:
            LOG.error("Error loading %s", file)
            raise
        services[svc.name] = svc
    LOG.info("Hanlding extra service dependencies...")
    return resolve_service_deps(services)


def resolve_service_deps(services: list) -> dict:
    """loop through services and handle needed_by"""
    needed_by = {}
    for name in services:
        service = services.get(name)
        needs = service.get_tasks_needed_by()
        for need, provides in needs.items():
            needed_by[need] = list(set(needed_by.get(need, []) + provides))
    for name in services:
        service = services.get(name)
        service.update_task_requires(needed_by)
    return services


def add_hosts_to_services(inventory, roles, services) -> dict:
    for host in inventory.hosts.keys():
        for svc in roles.get_services(inventory.hosts.get(host).get("role")):
            LOG.debug("Adding %s to %s", host, svc)
            try:
                services[svc].add_host(host)
            except KeyError as e:
                raise InvalidService(f"Service '{svc}' is not defined") from e
    return services


def add_services_to_flow(flow, services, task_type_override=None) -> gf.Flow:
    for service_id in services:
        service = services.get(service_id)
        if len(service.hosts) == 0:
            # skip services with no target hosts
            LOG.warning("Skipping adding service %s due to no hosts...", service.name)
            continue
        LOG.debug("Adding %s tasks...", service.name)
        try:
            for task in service.build_tasks(task_type_override):
                flow.add(task)
        except tf_exc.DependencyFailure:
            dot = networkx.drawing.nx_pydot.to_pydot(
                flow._graph  # pylint: disable=protected-access
            )
            dot.write_svg("failure.svg")
            LOG.error("Failure graph svg written out to failure.svg")
            raise
    return flow


def main():
    """task-core"""
    start = datetime.now()
    cli = Cli()
    args = cli.parse_args()

    setup_basic_logging(args.debug)
    mgr = TaskManager(args.services_dir, args.inventory_file, args.roles_file)
    flow = mgr.create_flow()

    if not args.noop:
        LOG.info("Starting execution...")
        e = engines.load(flow, executor="threaded", engine="parallel", max_workers=5)
        e.run()
        result = e.storage.fetch_all()
        LOG.info("Ran %s tasks...", len(result.keys()))
        LOG.info("Stats: %s", e.statistics)
    else:
        result = None
        try:
            mgr.write_flow_graph(flow, "noop.svg")
            LOG.info("Task graph written out to noop.svg")
        except UnavailableException:
            pass
        LOG.info("Skipping execution due to --noop...")
    end = datetime.now()
    LOG.info("Elapsed time: %s", end - start)
    LOG.info("Done...")
    LOG.debug(result)


def example():
    """task-core-example"""
    start = datetime.now()
    setup_basic_logging(True)

    services_dir = os.path.join(
        sys.prefix, "share", "task-core", "examples", "framework", "services"
    )
    inventory_file = os.path.join(
        sys.prefix, "share", "task-core", "examples", "framework", "inventory.yaml"
    )
    roles_file = os.path.join(
        sys.prefix, "share", "task-core", "examples", "framework", "roles.yaml"
    )
    mgr = TaskManager(services_dir, inventory_file, roles_file)
    flow = mgr.create_flow()

    LOG.info("Running...")
    result = engines.run(flow, engine="parallel")
    LOG.info("Ran %s tasks...", len(result.keys()))
    end = datetime.now()
    LOG.info("Elapsed time: %s", end - start)
    LOG.info("Done...")
    pprint.pprint(result)


if __name__ == "__main__":
    example()
