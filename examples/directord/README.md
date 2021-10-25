# Deploy an undercloud
```
# Provision 3ctl + 1 compute node and a vip
# Example node/vip configs for process
[stack@undercloud ~]$ cat provision.yaml
- name: Controller
  count: 3
  defaults: &inst_defaults
    config_drive:
      cloud_config:
        ssh_pwauth: true
        disable_root: false
        chpasswd:
          list: |-
            root:redhat
          expire: False
- name: Compute
  count: 1
  defaults: *inst_defaults


[stack@undercloud ~]$ cat network-vips.yaml
- network: ctlplane
  ip_address: 192.168.24.99
```

After provisioning the nodes, you should end up with a a file that contained
the post-provisioned heat vars ~/overcloud-baremetal-deployed.yaml. This file
path is assumed for future commands.

# Build task-core
```
# Build task-core
mkdir -p ~/rpmbuild/SOURCES
sudo dnf -y install yum-utils rpm-build dnf-plugins-core python3-pbr
git clone https://github.com/Directord/task-core

pushd ~/task-core/
git fetch --all && git checkout origin/poc
rm -rf dist/task-core-*.tar.gz ~/rpmbuild/SOURCES/task-core-*.tar.gz
python3 setup.py sdist
cp dist/task-core-*.tar.gz ~/rpmbuild/SOURCES/
# Adjust version as necessary
VER="$(ls dist/ | cut -d '-' -f 3 | sed 's/.tar.gz//' | sort -nr | head -1)"
rpmbuild -ba --define "released_version $VER" contrib/task-core.spec
sudo dnf -y localinstall ~/rpmbuild/RPMS/noarch/*${VER}*.rpm || sudo dnf -y update ~/rpmbuild/RPMS/noarch/*${VER}*.rpm
popd
```

# need iptables clear on undercloud for directord
```
sudo iptables -F
```
# Grab "Upload RPM artifact"

Fetch the latest stable Directord RPMS
``` shell
function get_latest_release() {
  curl --silent "https://api.github.com/repos/$1/releases/latest" |
    grep '"tag_name":' |
    sed -E 's/.*"([^"]+)".*/\1/'
}

rm -f rpm-bundle.tar.gz
rm -rf rpm-bundle

sudo dnf install -y wget
RELEASE="$(get_latest_release cloudnull/directord)"
mkdir rpm-bundle
pushd rpm-bundle
  wget https://github.com/cloudnull/directord/releases/download/${RELEASE}/rpm-bundle.tar.gz
  tar xf rpm-bundle.tar.gz
  sudo dnf localinstall -y $(ls -1 *.rpm | egrep -v '(src|debug)') || sudo dnf -y update $(ls -1 *.rpm | egrep -v '(src|debug)')
popd
```

# setup ansible.cfg to help with bootstrapping
```
# setup ansible for fixing stuff

cat > ~/.ansible.cfg <<EOF
[defaults]
host_key_checking = False
callback_whitelist = profile_tasks

[ssh_connection]
ssh_args = -o ForwardAgent=yes -o ControlMaster=auto -o ControlPersist=60s
pipelining = true
EOF
```

# generate ansible inventory for nodes
```
python3 /usr/share/task-core/contrib/example-tools/deployed2ansible.py ~/overcloud-baremetal-deployed.yaml -o ~/ansible_inventory.yaml
```
# needs to run on the overcloud nodes
```
# sudo dnf -y reinstall http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/Packages/centos-stream-repos-8-2.el8.noarch.rpm
ansible overcloud -i ~/ansible_inventory.yaml --become -m ansible.builtin.shell -a "dnf -y reinstall http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/Packages/centos-stream-repos-8-2.el8.noarch.rpm"
```

# on undercloud bootstrap directord

## generate catalog from deployed server
```
python3 /usr/share/task-core/contrib/example-tools/deployed2directord.py ~/overcloud-baremetal-deployed.yaml -o ~/directord_catalog.yaml
```

## run bootstrap
```
directord --debug bootstrap --catalog ~/directord_catalog.yaml --catalog /usr/share/directord/tools/directord-dev-bootstrap-catalog.yaml --key-file /home/stack/.ssh/id_rsa
```

## run bootstrap
````
directord --debug bootstrap --catalog directord_catalog.yaml --catalog /usr/share/directord/tools/directord-dev-bootstrap-catalog.yaml --key-file ~/.ssh/id_rsa
# set perms so your user can use directord
sudo chgrp $USER /var/run/directord.sock  && sudo chmod g+w /var/run/directord.sock
````

# example directord commands
```
directord manage --list-nodes
directord manage --list-jobs
# used to clear all the things
directord exec --verb CACHEEVICT all
directord manage --purge-jobs
```

# PoC

## Update configs
```
cd ~/task-core/examples/directord/undercloud/
```

Put IPs from hosts into config_options.yaml
 - edit tripleo_network_ips in config_options.yaml
 - edit tripleo_controller_ips in config_options.yaml
 - edit tripleo_cluster_addresses in config_options.yaml

## Run deployment
```
bash ~/task-core/examples/directord/undercloud/run_3ctl.sh
```
