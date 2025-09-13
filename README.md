# Nornir Validate

The idea behind this project is to to validate network state based on input files of desired device states. Nornir (with ***nornir-netmiko***) gathers and formats device outputs before feeding this into ***napalm-validate*** in the form of the ***actual_state*** and ***desired_state*** to produce a ***compliance report***. As the name suggests I have not reinvented the wheel here, I just extended [*napalm_validate*](https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py) to validate on commands rather than getters to allow for the flexibility of validating any command output.

In short the script works in the following manner:

- **Input file:** The *desired state* is defined in YAML format (can be automatically generated) and fed into the script at runtime
- **Desired state:** The *desired state* is rendered by Jinja adding the commands required for validation and saved as a *Nornir host_var*
- **Actual state:** *Netmiko* runs the commands against the devices parsing the outputs through *ntc-templates* before creating an *actual state* in the same format as the desired state
- **Compliance report:** The *desired state* and *actual state* are fed into *napalm_validate* compared creating a *compliance report* of the differences

Is a work in progress, has been refactored but needs testing and re-documenting in RTD.
