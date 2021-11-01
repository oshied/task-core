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
set -ex

RING=${1:-account}
POWER=${SWIFT_POWER:-10}
REPLICAS=${SWIFT_REPLICAS:-1}
MIN_PART_HOURS=${SWIFT_MIN_PART_HOURS:-1}
HOSTS=${SWIFT_HOSTS:-127.0.0.1}
PORT=${SWIFT_PORT:-6002}
DEVICES=${SWIFT_DEVICES:-d1}
REGION=${SWIFT_REGION:-1}
ZONE=${SWIFT_ZONE:-1}

RING_PATH="/etc/swift/${RING}.builder"
if ! test -f $RING_PATH; then
    swift-ring-builder $RING_PATH create $POWER $REPLICAS $MIN_PART_HOURS
fi

for HOST in $HOSTS; do
    for DEVICE in $DEVICES; do
        if ! swift-ring-builder $RING_PATH | awk '{print $4" "$6}' | grep -q "${HOST}:${PORT} $DEVICE"; then
            swift-ring-builder $RING_PATH \
                add --region $REGION --zone $ZONE --ip $HOST --port $PORT \
                --device $DEVICE --weight 100
        fi
    done
done



