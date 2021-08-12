#!/bin/bash

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



