task-core
=========

|CI Status|

.. |CI Status| image:: https://github.com/Directord/task-core/actions/workflows/py-tox.yml/badge.svg
   :target: https://github.com/Directord/task-core/actions

Install
~~~~~~~
.. code-block::

  pip install .

Example invocation (tests framework)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block::

  task-core-example

Example invocation (from folder)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block::

  task-core --services-dir examples/directord/services \
            --inventory-file examples/directord/inventory.yaml \
            --roles-file examples/directord/roles.yaml \
            --debug

Example directord execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is an example that uses [https://github.com/cloudnull/directord] to setup
an instance of keystone. The below bit of code assumes 4 nodes available
with a stack user that can been connected to via ssh from the user running
the bash script.

.. code-block::

    sudo dnf install python3-virtualenv git -y

    virtualenv ~/test-venv
    source ~/test-venv/bin/activate

    git clone https://github.com/Directord/task-core

    pip install directord

    pushd task-core
    pip install -r requirements.txt
    pip install .
    popd

    ssh-keygen -t rsa -f ~/.ssh/id_rsa -q -N ""
    for H in 2 3 4 5; do
      ssh-keyscan -H -t rsa 192.168.24.$H >> ~/.ssh/known_hosts
      ssh-copy-id 192.168.24.$H
    done

    cat > ~/catalog.yaml <<EOF
    directord_server:
      targets:
      - host: 192.168.24.2
        port: 22
        username: stack

    directord_clients:
      args:
        port: 22
        username: stack
      targets:
      - host: 192.168.24.3
      - host: 192.168.24.4
      - host: 192.168.24.5
    EOF

    directord bootstrap --catalog $HOME/catalog.yaml --catalog ~/test-venv/share/directord/tools/directord-bootstrap-catalog.yaml

    sudo chmod a+w /var/run/directord.sock

    cat > ~/inventory.yaml <<EOF
    hosts:
      standalone-1:
        role: keystone
      standalone-2:
        role: basic
      standalone-3:
        role: basic
    EOF

    task-core \
      -s task-core/examples/directord/services/ \
      -i $HOME/inventory.yaml \
      -r task-core/examples/directord/roles.yaml

    ssh standalone-1 openstack --os-auth-url http://standalone-1:5000/v3 --os-user-domain-name default --os-username admin --os-password keystone token issue
