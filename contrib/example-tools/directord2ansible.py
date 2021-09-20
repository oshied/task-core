# /usr/bin/env python3
"""script to convert service directord tasks to ansible roles

Example execution:
python3 contrib/example-tools/directord2ansible.py \
        -s examples/directord/services \
        -i examples/directord/basic/basic_inventory.yaml \
        -r examples/directord/basic/basic_roles.yaml \
        examples/ansible/
"""

import argparse

# import functools
import logging
import shutil
import os
import yaml

from taskflow import engines

# from taskflow import task as tftask
from taskflow.patterns import graph_flow as gf

import task_core.cmd
from task_core.inventory import Inventory
from task_core.inventory import Roles
from task_core.logging import setup_basic_logging

LOG = logging.getLogger(__name__)


def parse_args():
    """arguments for this script"""
    parser = argparse.ArgumentParser(
        description="directord service tasks to ansible roles"
    )
    parser.add_argument(
        "-s",
        "--services-dir",
        required=True,
        help=("Path to a directory containing service definitions"),
    )
    parser.add_argument(
        "-i",
        "--inventory-file",
        required=True,
        help=("Path to an inventory file containing hosts to role mappings"),
    )
    parser.add_argument(
        "-r",
        "--roles-file",
        required=True,
        help=("Path to a roles file containing roles to service mappings"),
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help=("Enable debug logging")
    )

    parser.add_argument(
        "ansible_directory",
        help="Output directory of the generated ansible roles",
    )
    return parser.parse_args()


# fold long lines
def str_presenter(dumper, data):
    if len(data) > 120:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


def process_add_task(args, role_dir, kargs, uargs):
    file_name = os.path.basename(uargs[0])
    if kargs.blueprint:
        ansible_action = "ansible.builtin.template"
        file_dir = os.path.join(role_dir, "templates")
        src_path = file_name
    else:
        ansible_action = "ansible.builtin.copy"
        file_dir = os.path.join(role_dir, "files")
        src_path = "{{ role_path }}/files/%s" % file_name
    os.makedirs(file_dir, exist_ok=True)
    src_file = os.path.normpath(os.path.join(args.services_dir, uargs[0]))
    shutil.copy(src_file, file_dir)
    data = {
        "name": "ADD",
        ansible_action: {"src": src_path, "dest": uargs[1]},
        "become": True,
    }
    if kargs.chown:
        chown = kargs.chown.split(":")
        data[ansible_action]["owner"] = chown[0]
        if len(chown) > 1 and chown[1]:
            data[ansible_action]["group"] = chown[1]
    if kargs.chmod:
        data[ansible_action]["mode"] = kargs.chmod
    return data


def process_cachefile_task(file_path, ansible_tasks):
    slurp = {
        "name": "CACHEFILE - slurp",
        "ansible.builtin.slurp": {
            "src": file_path,
        },
        "register": "vars_file",
    }
    ansible_tasks.append(slurp)
    copy = {
        "name": "CACHEFILE - copy",
        "ansible.builtin.copy": {
            "content": "{{ vars_file.content | b64decode }}",
            "dest": file_path,
        },
        "register": "vars_file",
        "delegate_to": "localhost",
    }
    ansible_tasks.append(copy)
    data = {
        "name": "CACHEFILE",
        "ansible.builtin.include_vars": file_path,
    }
    return data


def process_run_task(kargs, uargs, tasks):
    data = {
        "name": "RUN",
        "ansible.builtin.shell": " ".join(uargs),
        "run_once": kargs.run_once,
        "args": {"warn": False},
        "become": True,
    }
    if kargs.stdout_arg:
        data["register"] = "{}_stdout".format(kargs.stdout_arg)
        tasks.append(data)
        data = {
            "name": "RUN --stdout-arg",
            "ansible.builtin.set_fact": {
                kargs.stdout_arg: "{{ %s_stdout.stdout }}" % kargs.stdout_arg
            },
        }
    return data


def process_arg_task(uargs):
    # handle quoted vars which ned to be unquoted when we convert
    val = [v.strip('"') for v in uargs[1:]]
    data = {
        "name": "ARG",
        "ansible.builtin.set_fact": {uargs[0]: " ".join(val)},
    }
    return data


def process_query_task(uargs):
    query_jinja = [
        "{%- set q = {} -%}",
        "{%- set qvar = '",
        uargs[0],
        "' -%}",
        "{%- for h, v in hostvars.items() %}",
        "{%- if qvar in v %}",
        "{%- set _ = q.update({h: {qvar: v[qvar]}}) %}",
        "{%- endif %}",
        "{%- endfor %}",
        "{{ q | combine(query, recursive=True) }}",
    ]

    data = {"ansible.builtin.set_fact": {"query": "".join(query_jinja)}}
    return data


def process_service_task(kargs, uargs, tasks):
    if kargs.restarted:
        state = "restarted"
    elif kargs.stopped:
        state = "stopped"
    else:
        state = "started"
    data = None
    for svc in uargs:
        # only add services when we loop
        if data:
            tasks.append(data)
        data = {
            "name": "SERVICE",
            "ansible.builtin.service": {"name": svc, "state": state},
            "become": True,
        }
        if kargs.enable:
            data["ansible.builtin.service"]["enabled"] = True
        elif kargs.disable:
            data["ansible.builtin.service"]["enabled"] = False
    return data


def process_workdir_task(kargs, uargs):
    data = {
        "name": "WORKDIR",
        "ansible.builtin.file": {
            "path": " ".join(uargs),
            "state": "directory",
            "recurse": True,
        },
        "become": True,
    }
    if kargs.chown:
        chown = kargs.chown.split(":")
        data["ansible.builtin.file"]["owner"] = chown[0]
        if len(chown) > 1 and chown[1]:
            data["ansible.builtin.file"]["group"] = chown[1]
    if kargs.chmod:
        data["ansible.builtin.file"]["mode"] = kargs.chmod
    return data


def process_directord_jobs(
    args,
    role_dir,
    jobs,
):  # pylint: disable=too-many-branches,too-many-statements
    ansible_tasks = []
    job_parser = argparse.ArgumentParser(
        description="generic job parser", allow_abbrev=False, add_help=False
    )
    job_parser.add_argument("--blueprint", action="store_true")
    job_parser.add_argument("--run-once", action="store_true")
    job_parser.add_argument("--skip-cache", action="store_true")
    job_parser.add_argument("--timeout", type=int)
    job_parser.add_argument("--stdout-arg")
    job_parser.add_argument("--chown")
    job_parser.add_argument("--chmod")
    job_parser.add_argument("--restarted", action="store_true")
    job_parser.add_argument("--stopped", action="store_true")
    job_parser.add_argument("--enable", action="store_true")
    job_parser.add_argument("--disable", action="store_true")
    for job in jobs:
        data = None
        action = next(iter(job))
        cmd = job[action]
        kargs, uargs = job_parser.parse_known_args(cmd.split())
        if action in ("ADD", "COPY"):
            data = process_add_task(args, role_dir, kargs, uargs)
        elif action == "CACHEFILE":
            data = process_cachefile_task(cmd, ansible_tasks)
        elif action == "RUN":
            data = process_run_task(kargs, uargs, ansible_tasks)
        elif action == "ARG":
            data = process_arg_task(uargs)
        elif action == "QUERY":
            data = process_query_task(uargs)
        elif action == "SERVICE":
            data = process_service_task(kargs, uargs, ansible_tasks)
        elif action == "DNF":
            data = {
                "name": action,
                "ansible.builtin.package": {"name": uargs, "state": "present"},
                "become": True,
            }
        elif action == "WORKDIR":
            data = process_workdir_task(kargs, uargs)

        else:
            LOG.error("unknown action: %s", action)

        if data:
            ansible_tasks.append(data)
    return ansible_tasks


def generate_ansible_task_file(args, role_dir, task_dir, task):
    if task.driver not in ["directord"]:
        return
    file_name = "{}.yml".format(task.task_id)
    ansible_tasks = process_directord_jobs(args, role_dir, task.jobs)
    with open(os.path.join(task_dir, file_name), "w", encoding="utf-8") as task_file:
        yaml.safe_dump(ansible_tasks, task_file, width=120)


def generate_ansible_roles(args, svcs):
    roles_dir = os.path.join(args.ansible_directory, "roles")
    os.makedirs(roles_dir, exist_ok=True)
    for name, svc in svcs.items():
        LOG.info("Creating roles: %s", name)
        role_dir = os.path.join(roles_dir, name)
        os.makedirs(role_dir, exist_ok=True)
        svc_tasks = svc.build_tasks()
        if not svc_tasks:
            continue
        task_dir = os.path.join(role_dir, "tasks")
        os.makedirs(task_dir, exist_ok=True)
        for task in svc.build_tasks():
            LOG.info(" - %s", task.task_id)
            generate_ansible_task_file(args, role_dir, task_dir, task)


# def playbook_thingy(task, event_type, details):
#     if details.get('progress') == 1.0:
#         print("DONE! {}".format(task))


def add_services_to_flow(flow, services):
    """process services and add tasks to flow"""
    task_type_override = task_core.tasks.NoopTask
    for service_id in services:
        service = services.get(service_id)
        if len(service.hosts) == 0:
            LOG.warning("Skipping adding service %s due to no hosts...", service.name)
            continue
        LOG.debug("Adding %s tasks...", service.name)
        for task in service.build_tasks(task_type_override):
            # use this to do task progress updates
            # task.notifier.register(tftask.EVENT_UPDATE_PROGRESS,
            #                        functools.partial(playbook_thingy, task))
            flow.add(task)
    return flow


class PlaybookWriter:
    """class to handle graph to playbook"""

    def __init__(self, playbook_path, playbook_name="generated-plays.yml"):
        self._playbook_path = os.path.join(playbook_path, playbook_name)
        # we need to set query to an empty dict because query in ansible
        # is leaked Template object
        self._plays = [
            {
                "hosts": "all",
                "tasks": [
                    {"name": "setup vars", "ansible.builtin.set_fact": {"query": {}}}
                ],
            }
        ]
        self._current_play = None
        self._current_hosts = None

    def __del__(self):
        self.close()

    def task_transition(self, state, details):
        """update play based on task transition"""
        LOG.debug("State change: %s", state)
        data = details.get("result")[0].data
        hosts = data.get("hosts")
        if self._current_hosts != hosts:
            LOG.debug("Hosts change to... %s", hosts)
            if self._current_play:
                self._plays.append(self._current_play)
            self._current_play = {"hosts": ",".join(hosts), "tasks": []}
            self._current_hosts = hosts
        role_name = details.get("task_name").replace("-{}".format(data.get("id")), "")
        task = {
            "name": details.get("task_name"),
            "include_role": {
                "name": role_name,
                "tasks_from": "{}.yml".format(data.get("id")),
            },
        }
        self._current_play["tasks"].append(task)

    def close(self):
        with open(self._playbook_path, "w", encoding="utf-8") as playbook:
            yaml.safe_dump(self._plays, playbook, width=120)


def generate_ansible_playbook(args, svcs):
    inventory = Inventory(args.inventory_file)
    roles = Roles(args.roles_file)
    task_core.cmd.add_hosts_to_services(inventory, roles, svcs)
    flow = gf.Flow("root")
    add_services_to_flow(flow, svcs)
    playwriter = PlaybookWriter(args.ansible_directory)
    e = engines.load(flow, engine="serial")
    e.atom_notifier.register("SUCCESS", playwriter.task_transition)
    LOG.info("Compiling...")
    e.compile()
    LOG.info("Preparing...")
    e.prepare()
    LOG.info("Running...")
    e.run()
    LOG.info("Done: %s", e.statistics)


if __name__ == "__main__":
    cli_args = parse_args()
    setup_basic_logging(cli_args.debug)
    processed_svcs = task_core.cmd.load_services(cli_args.services_dir)
    generate_ansible_roles(cli_args, processed_svcs)
    generate_ansible_playbook(cli_args, processed_svcs)
