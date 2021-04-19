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
from task_core.service import Service
from task_core.inventory import Inventory
from task_core.inventory import Roles

logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] %(message)s", level=logging.INFO
)

LOG = logging.getLogger(__name__)


class Cli:
    """task-core cli"""
    def __init__(self):
        self._parser = argparse.ArgumentParser(
            description=""
        )

    @property
    def parser(self):
        return self._parser

    def parse_args(self):
        self.parser.add_argument(
            "-s", "--services-dir",
            required=True,
            help=("Path to a directory containing service definitions"),
        )
        self.parser.add_argument(
            "-i", "--inventory-file",
            required=True,
            help=("Path to an inventory file containing hosts to role mappings"),
        )
        self.parser.add_argument(
            "-r", "--roles-file",
            required=True,
            help=("Path to a roles file containing roles to service mappings"),
        )
        self.parser.add_argument(
            "-d", "--debug",
            action="store_true",
            default=False,
            help=("Enable debug logging")
        )
        args = self.parser.parse_args()
        return args


def load_services(services_dir) -> dict:
    LOG.info("Loading services from: %s", services_dir)
    files = glob.glob(os.path.join(services_dir, "**", "*.yaml"), recursive=True)
    services = {}
    for file in files:
        svc = Service(file)
        services[svc.name] = svc
    return services


def add_hosts_to_services(inventory, roles, services) -> dict:
    for host in inventory.hosts.keys():
        for svc in roles.get_services(inventory.hosts.get(host).get("role")):
            LOG.info("Adding %s to %s", host, svc)
            services[svc].add_host(host)
    return services


def add_services_to_flow(flow, services) -> gf.Flow:
    for service_id in services:
        service = services.get(service_id)
        LOG.info("Adding %s tasks...", service.name)
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
    services = load_services(args.services_dir)
    inventory = Inventory(args.inventory_file)
    roles = Roles(args.roles_file)

    add_hosts_to_services(inventory, roles, services)

    flow = gf.Flow("root")
    add_services_to_flow(flow, services)

    LOG.info("Running...")
    result = engines.run(flow, engine="parallel")
    pprint.pprint(result)


def example():
    """task-core-example"""
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
    pprint.pprint(result)


if __name__ == "__main__":
    example()
