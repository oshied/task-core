# /usr/bin/env python3
"""script to convert deployed yaml from tripleo to a directord catalog"""

import argparse
import os
import yaml


def parse_args():
    """arguments for this script"""
    parser = argparse.ArgumentParser(
        description="deployed server yaml to directord yaml"
    )
    parser.add_argument(
        "input_yaml", help="openstack overcloud node provision output yaml"
    )
    parser.add_argument(
        "-u",
        "--user",
        dest="ssh_user",
        default="heat-admin",
        required=False,
        help="remote host ssh user",
    )
    parser.add_argument(
        "-p",
        "--ssh-port",
        dest="ssh_port",
        default=22,
        help="remote host ssh port",
    )
    parser.add_argument(
        "-n",
        "--network",
        dest="network",
        default="ctlplane",
        required=False,
        help="network name to use",
    )
    parser.add_argument(
        "--server-address",
        default="192.168.24.2",
        help="Directord server address. Defaults to 192.168.24.2",
    )
    parser.add_argument(
        "--local-user",
        dest="local_ssh_user",
        default=os.environ.get("USER", "stack"),
        help="local user for ssh",
    )
    parser.add_argument(
        "--local-ssh-port",
        dest="local_ssh_port",
        default=22,
        help="remote host ssh port",
    )

    parser.add_argument(
        "-o", dest="output_yaml", required=False, help="directord catalog file name"
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
    server_addr = script_args.server_address
    ssh_user = script_args.ssh_user
    ssh_port = script_args.ssh_port
    local_user = script_args.local_ssh_user
    local_port = script_args.local_ssh_port
    inv = {
        "directord_server": {
            "args": {"port": local_port, "username": local_user},
            "targets": [{"host": server_addr}],
        },
        "directord_clients": {
            "args": {"port": ssh_port, "username": ssh_user},
            "targets": [],
        },
    }
    hosts = inv["directord_clients"]["targets"]

    for _, ipaddr in host_data.items():
        hosts.append({"host": ipaddr})

    inv_yaml = yaml.safe_dump(inv)
    if output:
        with open(output, encoding="utf-8", mode="w+") as output_file:
            output_file.write(inv_yaml)
        print("Catalog written to {}".format(output))
    else:
        print(inv_yaml)


if __name__ == "__main__":
    args = parse_args()
    data = parse_yaml(args.input_yaml, args.network)
    generate_inventory(data, args)
