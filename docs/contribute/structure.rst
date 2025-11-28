Feature Structure (-cf)
=======================

Generate the test directory, feature directory, base files (templated from `skelton_new_feature <https://github.com/sjhloco/nornir_validate/tree/main/skeleton_new_feature>`_) and sub-feature_index using the ``-cf`` (*--create_feature*) flag. This step is always required no matter whether you are creating a new feature, new sub-feature or adding an os_type to an existing sub-feature. Only directories and files that do not already exist will be created.

.. code-block:: bash

    python feature_builder.py -cf <ostype> <feature.sub-feature>

For example, ``python feature_builder.py -cf cisco_viptela sdwan.omp`` will create the following:

.. code-block:: bash

    ├── feature_templates
    │   ├── sdwan
    │   │   ├── sdwan_actual_state.py        # Template with the base Python structure to follow
    │   │   └── sdwan_desired_state.j2       # Template with the base Jinja structure to follow
    ├── tests
    │   ├── os_test_files
    │   │   ├── cisco_viptela
    │   │   │   ├── sdwan                    # Folder that will hold all the test files
    │   │   │   ├── subfeature_index.yml     # Index of all features and sub-features for this os_type, will be updated if already exists           

Index
-----

The **subfeature_index.yml** is automatically created or updated, it is used for unit-testing and the generation of validation files if no index is specified. The below snippet shows the *system* feature with its *image, mgmt_acl* and *module* sub-features.

.. code-block:: yaml
    
  all:
    system:
      - image
      - mgmt_acl: ["TEST_SSH_ACCESS", "TEST_SNMP_ACCESS"]
      - module

.. note::

    The majority of the time sub-features will be a string, however for more complex validations that require multiple commands (VRF route-tables, ACLs, etc) this will be a dictionary of lists. In these situations the *subfeature_index.yml* file will need to be edited manually.


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
