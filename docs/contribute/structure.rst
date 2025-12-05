Feature Structure (-cf)
=======================

Generate the test directory, feature directory, base files (templated from `newfeature_skeleton <https://github.com/sjhloco/nornir-validate/tree/main/newfeature_skeleton>`_) and sub-feature_index using the ``-cf`` (*--create_feature*) flag. This step is always required no matter whether you are creating a new feature, new sub-feature or adding an os_type to an existing sub-feature. Only directories and files that do not already exist will be created.

.. code-block:: bash

    python scripts/feature_builder.py -cf <ostype> <feature.sub-feature>

For example, ``python scripts/feature_builder.py -cf cisco_viptela sdwan.omp`` will create the following:

.. code-block:: bash

    ├── feature_templates
    │   ├── sdwan
    │   │   ├── sdwan_actual_state.py        # Template with the base Python structure to follow
    │   │   └── sdwan_desired_state.j2       # Template with the base Jinja structure to follow
    ├── tests
    │   ├── os_test_files
    │   │   ├── cisco_viptela
    │   │   │   ├── sdwan                    # Folder that will hold all the test files          

Index
-----

As part of the script the `index_files <https://github.com/sjhloco/nornir-validate/tree/main/src/nornir_validate/index_files>`_ **all_index.yml** and **os_type_index.yml** are updated (created if don't yet exist) with the former used for generation of validation files (if no index file specified) and the later for unit-testing. The below snippet shows the *system* feature with its *image, mgmt_acl* and *module* sub-features.

.. code-block:: yaml
    
  all:
    system:
      - image
      - mgmt_acl: [TEST_SSH_ACCESS, TEST_SNMP_ACCESS]
      - module

.. note::

    The majority of the time sub-features will be a string, however for more complex validations that require multiple commands (VRF route-tables, ACLs, etc) this will be a dictionary of list. In these situations the *xx_index.yml* file will need to be edited manually.


Test Inventory
--------------

If the sub-feature is for a new *os_type* you will need to create a new group within **tests/test_inventory/groups.yml**

.. code-block:: yaml
    
  viptela:
    connection_options:
      netmiko:
        platform: cisco_viptela

and add a dummy host to **tests/test_inventory/hosts_inventory.yml**.

.. code-block:: yaml
    
    viptela_host:
      hostname: 10.10.10.1
      groups: [viptela]
