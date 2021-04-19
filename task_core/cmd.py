#!/usr/bin/env python3
"""task-core cli"""
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
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO)

LOG = logging.getLogger(__name__)


def main():
    services_dir = os.path.join(sys.prefix, "share", "task-core", "services")
    LOG.info(f"Loading services from: {services_dir}")
    files = glob.glob(os.path.join(services_dir, "**", "*.yaml"), recursive=True)
    services = {}
    for file in files:
        svc = Service(file)
        services[svc.name] = svc

    inventory_file = os.path.join(sys.prefix, "share", "task-core", "examples", "inventory.yaml")
    inventory = Inventory(inventory_file)

    roles_file = os.path.join(sys.prefix, "share", "task-core", "examples", "roles.yaml")
    roles = Roles(roles_file)

    for host in inventory.hosts.keys():
        for svc in roles.get_services(inventory.hosts.get(host).get('role')):
            LOG.info(f"Adding {host} to {svc}")
            services[svc].add_host(host)

    flow = gf.Flow("root")
    for service_id in services.keys():
        service = services.get(service_id)
        LOG.info(f"Adding {service.name} tasks...")
        service_flow = gf.Flow(service.name)
        for task in service.tasks:
            service_flow.add(task)
        flow.add(service_flow)

    LOG.info("Running...")
    result = engines.run(flow, engine="parallel")
    pprint.pprint(result)


if __name__ == "__main__":
    main()
