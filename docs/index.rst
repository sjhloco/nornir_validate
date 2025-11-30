Nornir Validate Documentation
=============================

A Nornir plugin for validating network state (*actual state*) against YAML-based specifications (*desired state*). This project extends `napalm-validate <https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py>`_ to perform command-based validation rather than relying solely on getters, providing greater flexibility in validating arbitrary command outputs. It leverages Nornir with `nornir-netmiko` to collect and format device data, then compares **actual state** against **desired state** to generate a **compliance report**.

How It Works
------------

1. **Validation File**: The expected *desired state* specified in YAML format (can be automatically generated) is provided at runtime
2. **Desired State**: The *validation file* is rendered by `Jinja <https://jinja.palletsprojects.com/en/stable/>`_ adding validation commands to the *desired state* and storing this as a Nornir host variable
3. **Data Collection**: `Nornir <https://github.com/nornir-automation/nornir>`_ (`netmiko plugin <https://github.com/ktbyers/nornir_netmiko>`_) executes commands against target devices parsing the outputs through `ntc-templates <https://github.com/networktocode/ntc-templates>`_ to construct the *actual state*
4. **Compliance Report**: The *desired state* and *actual state* are fed into `napalm-validate <https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py>`_  generating a *compliance report* of the differences

.. image:: https://private-user-images.githubusercontent.com/33333983/520476424-879a2aaa-15a5-45f3-9f6d-37814f1703f4.gif?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjQ0OTg2ODMsIm5iZiI6MTc2NDQ5ODM4MywicGF0aCI6Ii8zMzMzMzk4My81MjA0NzY0MjQtODc5YTJhYWEtMTVhNS00NWYzLTlmNmQtMzc4MTRmMTcwM2Y0LmdpZj9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTExMzAlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUxMTMwVDEwMjYyM1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTYzNTA4N2E0M2I0YTI2MzAxMjYwZTMzYjA4YzJjMThmOWU0M2YwYTM5ZjU4MzUxZmRlY2Y4ZGYyNTlmNjc5MjYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.LKiKujC_7UOc8z7HeiR3W3r5AASvUq3JjdsZtcIYQH0
   
   :alt: Compliance report animation

Contents
--------

* :doc:`Validations <validations>` - A table of all the current supported validations and validation nuances
* :doc:`Tutorial <tutorial/index>` - Contains all the information you require to get started with nornir-validate
* :doc:`Contribute <contribute/index>` - Runs through how to contribute new validation models to the project

.. toctree::
   :hidden:
   :maxdepth: 3

   Home <self>
   validations
   tutorial/index
   contribute/index
