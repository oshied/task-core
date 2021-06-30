#!/usr/bin/env python3
"""task-core cli"""
import argparse
import glob
import logging
import os
import pprint
import sys

from taskflow import engines
from taskflow.patterns import graph_flow as gf

from .exceptions import InvalidService
from .inventory import Inventory
from .inventory import Roles
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
        args = self.parser.parse_args()
        return args


def load_services(services_dir) -> dict:
    files = glob.glob(os.path.join(services_dir, "**", "*.yaml"), recursive=True)
    services = {}
    for file in files:
        svc = Service(file)
        services[svc.name] = svc
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


def add_services_to_flow(flow, services) -> gf.Flow:
    for service_id in services:
        service = services.get(service_id)
        if len(service.hosts) == 0:
            # skip services with no target hosts
            LOG.debug("Skipping adding service %s due to no hosts...", service.name)
            continue
        LOG.debug("Adding %s tasks...", service.name)
        service_flow = gf.Flow(service.name)
        for task in service.build_tasks():
            service_flow.add(task)
        flow.add(service_flow)
    return flow


def main():
    """task-core"""
    cli = Cli()
    args = cli.parse_args()

    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)s] %(message)s", level=log_level
    )
    LOG.info("Loading services from %s", args.services_dir)
    services = load_services(args.services_dir)
    LOG.info("Loading inventory from %s....", args.inventory_file)
    inventory = Inventory(args.inventory_file)
    LOG.info("Loading roles from %s....", args.roles_file)
    roles = Roles(args.roles_file)

    LOG.info("Adding hosts to services...")
    add_hosts_to_services(inventory, roles, services)

    flow = gf.Flow("root")
    LOG.info("Adding services to flow...")
    add_services_to_flow(flow, services)

    LOG.info("Starting execution...")
    # NOTE(mwhahaha): directord doesn't work with parallel, use serial for now
    result = engines.run(flow, engine="serial")
    LOG.info("Ran %s tasks...", len(result.keys()))
    LOG.info("Done...")
    pprint.pprint(result)


def example():
    """task-core-example"""
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)s] %(message)s", level=logging.DEBUG
    )

    services_dir = os.path.join(
        sys.prefix, "share", "task-core", "examples", "framework", "services"
    )
    services = load_services(services_dir)

    inventory_file = os.path.join(
        sys.prefix, "share", "task-core", "examples", "framework", "inventory.yaml"
    )
    inventory = Inventory(inventory_file)

    roles_file = os.path.join(
        sys.prefix, "share", "task-core", "examples", "framework", "roles.yaml"
    )
    roles = Roles(roles_file)

    add_hosts_to_services(inventory, roles, services)

    flow = gf.Flow("root")
    add_services_to_flow(flow, services)

    LOG.info("Running...")
    result = engines.run(flow, engine="parallel")
    LOG.info("Ran %s tasks...", len(result.keys()))
    pprint.pprint(result)


if __name__ == "__main__":
    example()
