"""Generate sample scale data"""
import random
import yaml

# generate 1000 hosts
HOST_COUNT = 1000
# generate 100 roles
ROLE_COUNT = int(HOST_COUNT / 10)
# generate 1000 services
SERVICE_COUNT = 1000


def dump_yaml(filename, data):
    print(f"Outputting {filename}...")
    with open(filename, encoding="utf-8", mode="w") as outfile:
        yaml.dump(data, outfile, default_flow_style=False)


def gen_scale_data():
    # generate inventory data
    inventory = {"hosts": {}}
    for host in range(0, HOST_COUNT):
        inventory["hosts"][f"host-{host:04}"] = {"role": f"role-{host % ROLE_COUNT}"}
    dump_yaml("inventory.yaml", inventory)

    # generate roles data
    roles = {}
    roles_services = []
    for role in range(0, ROLE_COUNT):
        services = []
        for service in random.sample(range(SERVICE_COUNT), k=random.randrange(1, 20)):
            services.append(f"service-{service}")
        roles[f"role-{role}"] = {"services": services}
        roles_services.extend(services)

    dump_yaml("roles.yaml", roles)

    # create sample services and relationship data
    provides = []
    for svc in range(0, SERVICE_COUNT):
        service_id = f"service-{svc}"
        service = {
            "id": service_id,
            "type": "service",
            "version": "1.0.0",
            "tasks": [],
        }
        service_task_provides = []
        for tsk in range(random.randrange(1, 5)):
            task_id = f"task-{tsk}"
            task_provides = f"{service_id}-{task_id}"
            task = {
                "id": f"task-{tsk}",
                "driver": "print",
                "message": f"{service_id} -> {task_id}",
                "provides": [task_provides],
                "requires": [],
            }
            # add previous task requirement
            if tsk > 0:
                task["requires"].append(f"{service_id}-task-{tsk-1}")
            # occasionally add up to 3 additional tasks to requires
            if (
                len(provides) > 0
                and service_id in roles_services
                and random.randrange(0, 100) > 75
            ):
                task["requires"].extend(
                    random.sample(
                        provides, k=random.randrange(1, min(3, len(provides)))
                    )
                )
            service_task_provides.append(task_provides)
            service["tasks"].append(task)
        # add provides at the end to prevent service tasks from requiring tasks
        # from this service only if the service is defined in a role
        if service_id in roles_services:
            provides.extend(service_task_provides)

        dump_yaml(f"services/{service_id}.yaml", service)


if __name__ == "__main__":
    gen_scale_data()
