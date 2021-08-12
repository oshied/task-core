#!/bin/bash
# NOTE: edit 3ctl_inventory.yaml and config_options.yaml with your evironment
# defaults before continuing

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# we must be in the services dir because the services ADD commands
# assume we're in services/
pushd $SCRIPT_DIR/../services
set -ex
task-core -s . -i ../undercloud/3ctl_inventory.yaml -r ../undercloud/3ctl_roles.yaml -d
popd
