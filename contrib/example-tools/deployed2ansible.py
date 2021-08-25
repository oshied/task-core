#!/usr/bin/env python3
"""script to convert deployed yaml from tripleo to an ansible inventory"""

import argparse
import platform
import yaml


def parse_args():
    """arguments for this script"""
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
    """parse deploy yaml"""
    with open(yaml_file, encoding="utf-8", mode="r") as file_handle:
        yaml_data = yaml.safe_load(file_handle)
    nodes = yaml_data.get("parameter_defaults", {}).get("NodePortMap")
    if not nodes:
        raise Exception("NodePortMap missing from {}".format(yaml_file))
    return_data = {}
    for node, v in nodes.items():
        if not v.get(network):
            raise Exception("{} network is missing from data".format(network))
        return_data[node] = v.get(network).get("ip_address")

    return return_data


def generate_inventory(host_data, script_args):
    """generate ansible inventory yaml"""
    output = script_args.output_yaml
    ssh_user = script_args.ssh_user
    local_node = platform.node().split(",", 1)[0]
    inv = {
        "all": {
            "hosts": {local_node: {"ansible_connection": "local"}},
            "children": {},
        }
    }
    hosts = inv["all"]["hosts"]
    children = inv["all"]["children"]

    for node, ipaddr in host_data.items():
        hosts[node] = {"ansible_host": ipaddr, "ansible_user": ssh_user}
        parts = node.split("-")
        parts_count = len(parts)
        if parts_count >= 2:
            for i in range(parts_count - 1):
                if not children.get(parts[i]):
                    children[parts[i]] = {"hosts": {node: {}}}
                else:
                    children[parts[i]]["hosts"][node] = {}
        else:
            raise Exception(
                "Unable to handle hostname format. Format expects "
                "role-# or cloud-role-#"
            )
    inv_yaml = yaml.safe_dump(inv)
    if output:
        with open(output, encoding="utf-8", mode="w+") as output_file:
            output_file.write(inv_yaml)
        print("Inventory written to {}".format(output))
    else:
        print(inv_yaml)


if __name__ == "__main__":
    args = parse_args()
    data = parse_yaml(args.input_yaml, args.network)
    generate_inventory(data, args)
