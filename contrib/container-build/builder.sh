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
set -e

RPM_DIR=${RPM_DIR:-/home/builder/rpm}
ARTIFACT_DIR="build-$(date +%s)"
ARTIFACT_PATH=${ARTIFACT_PATH:-"${RPM_DIR}/$ARTIFACT_DIR"}
TASK_SPEC=${TASK_SPEC:-task-core.spec}
SPEC_PATH="${RPM_DIR}/${TASK_SPEC}"
RELEASE_VERSION=${RELEASE_VERSION:-0.0.1}

sudo chown builder: $RPM_DIR

echo "Creating artifact directory: $ARTIFACT_DIR"
mkdir -p $ARTIFACT_PATH

echo "Installing build deps..."
echo "Logging to $ARTIFACT_DIR/builddep.log"
sudo dnf -y builddep "${RPM_DIR}/${TASK_SPEC}" &> $ARTIFACT_PATH/builddep.log

echo "Building: $SPEC_PATH"
echo "Logging to $ARTIFACT_DIR/rpmbuild.log"
rpmbuild --undefine=_disable_source_fetch \
         --define "release_version $RELEASE_VERSION" \
         -ba $SPEC_PATH &> $ARTIFACT_PATH/rpmbuild.log

echo "Copying rpms to $ARTIFACT_DIR"
find /home/builder/build -name '*.rpm' -exec cp "{}" $ARTIFACT_PATH \;

# fixup permissions
USER_IDS=$(stat --format="%u:%g" $SPEC_PATH)
sudo chown $USER_IDS $RPM_DIR
sudo chown $USER_IDS -R $ARTIFACT_PATH
echo "Done!"
