#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# NOTE: edit 3ctl_inventory.yaml and config_options.yaml with your evironment
# defaults before continuing

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# we must be in the services dir because the services ADD commands
# assume we're in services/
pushd $SCRIPT_DIR/../services
set -ex
task-core -s . -i ../undercloud/3ctl_inventory.yaml -r ../undercloud/3ctl_roles.yaml -d
popd
