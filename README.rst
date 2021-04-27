task-core
=========

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

  task-core --services-dir examples/director/services \
            --inventory-file examples/director/inventory.yaml \
            --roles-file examples/director/roles.yaml \
            --debug
