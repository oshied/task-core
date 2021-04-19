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

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO)

LOG = logging.getLogger(__name__)

def main():
    data = os.path.join(sys.prefix, "share", "task-core", "services")
    LOG.info(f"Loading data from: {data}")
    files = glob.glob(os.path.join(data, "**", "*.yaml"), recursive=True)
    services = []
    for file in files:
        services.append(Service(file))

    flow = gf.Flow("root")
    for service in services:
        LOG.info(f"Adding {service.id} tasks...")
        service_flow = gf.Flow(service.id)
        for task in service.tasks:
            service_flow.add(task)
        flow.add(service_flow)

    LOG.info("Running...")
    result = engines.run(flow, engine="parallel")
    pprint.pprint(result)


if __name__ == "__main__":
    main()
