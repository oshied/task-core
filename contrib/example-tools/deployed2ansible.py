#!/usr/bin/env python3

import argparse
import platform
import yaml


def parse_args():
    parser = argparse.ArgumentParser(
        description="deployed server yaml to ansible inventory"
    )
    parser.add_argument(
        "input_yaml", help="openstack overcloud node provision output yaml"
    )
    parser.add_argument(
        "-u",
        dest="ssh_user",
        default="heat-admin",
        required=False,
        help="host ssh user",
    )
    parser.add_argument(
        "-n",
        dest="network",
        default="ctlplane",
        required=False,
        help="network name to use",
    )
    parser.add_argument(
        "-o", dest="output_yaml", required=False, help="ansible inventory file name"
    )
    return parser.parse_args()


def parse_yaml(yaml_file, network):
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f)
    nodes = data.get("parameter_defaults", {}).get("NodePortMap")
    if not nodes:
        raise Exception("NodePortMap missing from {}".format(yaml_file))
    return_data = {}
    for node, v in nodes.items():
        if not v.get(network):
            raise Exception("{} network is missing from data".format(network))
        return_data[node] = v.get(network).get("ip_address")

    return return_data


def generate_inventory(data, args):
    output = args.output_yaml
    ssh_user = args.ssh_user
    local_node = platform.node().split(",", 1)[0]
    inv = {
        "all": {
            "hosts": {local_node: {"ansible_connection": "local"}},
            "children": {},
        }
    }
    hosts = inv["all"]["hosts"]
    children = inv["all"]["children"]

    for node, ip in data.items():
        hosts[node] = {"ansible_host": ip, "ansible_user": ssh_user}
        parts = node.split("-")
        parts_count = len(parts)
        if parts_count >= 2:
            for x in range(parts_count - 1):
                if not children.get(parts[x]):
                    children[parts[x]] = {node: {}}
                else:
                    children[parts[x]][node] = {}
        else:
            raise Exception(
                "Unable to handle hostname format. Format expects "
                "role-# or cloud-role-#"
            )
    data_yaml = yaml.safe_dump(inv)
    if output:
        with open(output, "w+") as f:
            f.write(data_yaml)
        print("Inventory written to {}".format(output))
    else:
        print(data_yaml)


if __name__ == "__main__":
    args = parse_args()
    data = parse_yaml(args.input_yaml, args.network)
    generate_inventory(data, args)
