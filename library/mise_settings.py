#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025, Stoney Jackson
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: mise_settings
short_description: Manage mise settings
version_added: "1.0.0"
description:
    - Manages mise settings in the global or local config file.
    - This is equivalent to running C(mise settings set/unset) from the command line.
    - Settings are stored in C(~/.config/mise/config.toml) by default.
options:
    name:
        description:
            - The name of the setting to manage (e.g. C(auto_update), C(trusted_config_paths)).
            - Required when O(state=present) or O(state=absent).
        type: str
    value:
        description:
            - The value to set for the setting.
            - Required when O(state=present).
            - Can be a string, number, boolean, or list depending on the setting.
        type: raw
    state:
        description:
            - Whether the setting should be present or absent.
            - V(present) sets the setting to the given value.
            - V(absent) removes the setting.
            - V(get) retrieves the current value (read-only).
        type: str
        default: present
        choices: ['present', 'absent', 'get']
    local:
        description:
            - Use the local config file instead of the global one.
            - When true, modifies the local config file in the current directory.
        type: bool
        default: false
    executable:
        description:
            - Path to the mise executable.
            - If not specified, the module will search for C(mise) in C(PATH).
        type: str
requirements:
    - mise L(https://mise.jdx.dev/) installed and available in C(PATH) or specified via O(executable).
author:
    - Stoney Jackson (@stoney)
seealso:
    - name: mise documentation for mise settings
      link: https://mise.jdx.dev/cli.html#mise-settings
      description: Official documentation for the C(mise settings) command.
"""

EXAMPLES = r"""
- name: Set auto_update to true
  community.general.mise_settings:
    name: auto_update
    value: true

- name: Add a trusted config path
  community.general.mise_settings:
    name: trusted_config_paths
    value: "/"
    state: present

- name: Get the current value of auto_update
  community.general.mise_settings:
    name: auto_update
    state: get
  register: result

- name: Remove a setting
  community.general.mise_settings:
    name: auto_update
    state: absent

- name: Set a setting in local config
  community.general.mise_settings:
    name: node.mirror_url
    value: "https://npmmirror.com/mirrors/node/"
    local: true
"""

RETURN = r"""
name:
    description: The setting name.
    type: str
    returned: always
value:
    description: The setting value (for O(state=present) and O(state=get)).
    type: raw
    returned: when O(state=present) or O(state=get)
state:
    description: The desired state.
    type: str
    returned: always
local:
    description: Whether the local config was used.
    type: bool
    returned: always
changed:
    description: Whether the module made changes.
    type: bool
    returned: always
"""

import os
import json

from ansible.module_utils.basic import AnsibleModule


def _find_mise(module):
    """Locate the mise executable."""
    exe = module.params.get("executable")
    if exe and os.path.isfile(exe) and os.access(exe, os.X_OK):
        return exe

    rc, _, _ = module.get_bin_path("mise", required=False)
    if rc == 0:
        return module.get_bin_path("mise", required=True)

    module.fail_json(
        msg="mise executable not found. Install mise or specify the 'executable' parameter."
    )


def _get_setting(mise_path, setting_name, use_local, module):
    """Get the current value of a setting."""
    cmd = [mise_path, "settings", "get"]
    if use_local:
        cmd.append("--local")
    cmd.append(setting_name)

    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        # Setting might not exist
        return None

    value = stdout.strip()
    # Try to parse as JSON for complex values
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def _settings_list(mise_path, use_local, module):
    """Get all settings as JSON."""
    cmd = [mise_path, "settings", "ls", "--json"]
    if use_local:
        cmd.append("--local")

    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        return {}

    try:
        return json.loads(stdout) if stdout.strip() else {}
    except (ValueError, KeyError):
        return {}


def main():
    spec = dict(
        name=dict(type="str"),
        value=dict(type="raw"),
        state=dict(type="str", default="present", choices=["present", "absent", "get"]),
        local=dict(type="bool", default=False),
        executable=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        required_if=[
            ("state", "present", ["name", "value"]),
            ("state", "absent", ["name"]),
            ("state", "get", ["name"]),
        ],
        supports_check_mode=True,
    )

    setting_name = module.params["name"]
    value = module.params["value"]
    state = module.params["state"]
    use_local = module.params["local"]

    mise_path = _find_mise(module)

    if state == "get":
        current_value = _get_setting(mise_path, setting_name, use_local, module)
        module.exit_json(
            changed=False,
            name=setting_name,
            value=current_value,
            state=state,
            local=use_local,
        )

    elif state == "present":
        current_value = _get_setting(mise_path, setting_name, use_local, module)

        # Normalize value for comparison
        if value == current_value:
            module.exit_json(
                changed=False,
                name=setting_name,
                value=current_value,
                state=state,
                local=use_local,
                msg="Setting '{0}' is already set to the desired value.".format(
                    setting_name
                ),
            )

        # Build the mise settings set command
        cmd = [mise_path, "settings", "set"]
        if use_local:
            cmd.append("--local")
        cmd.append(setting_name)

        # Convert value to string for the command
        if isinstance(value, bool):
            cmd.append("true" if value else "false")
        elif isinstance(value, list):
            # For list values, set each element separately or use JSON
            for item in value:
                set_cmd = [mise_path, "settings", "set"]
                if use_local:
                    set_cmd.append("--local")
                set_cmd.extend([setting_name, str(item)])
                rc, stdout, stderr = module.run_command(set_cmd)
                if rc != 0:
                    module.fail_json(
                        msg="Failed to run 'mise settings set': {0}".format(stderr)
                    )
            module.exit_json(
                changed=True,
                name=setting_name,
                value=value,
                state=state,
                local=use_local,
                msg="Setting '{0}' has been updated.".format(setting_name),
            )
        else:
            cmd.append(str(value))

        if module.check_mode:
            module.exit_json(
                changed=True,
                name=setting_name,
                value=value,
                state=state,
                local=use_local,
            )

        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            module.fail_json(
                msg="Failed to run 'mise settings set': {0}".format(stderr)
            )

        module.exit_json(
            changed=True,
            name=setting_name,
            value=value,
            state=state,
            local=use_local,
            stdout=stdout,
            stderr=stderr,
            msg="Setting '{0}' has been updated.".format(setting_name),
        )

    elif state == "absent":
        current_value = _get_setting(mise_path, setting_name, use_local, module)
        if current_value is None:
            module.exit_json(
                changed=False,
                name=setting_name,
                state=state,
                local=use_local,
                msg="Setting '{0}' is not set.".format(setting_name),
            )

        # Build the mise settings unset command
        cmd = [mise_path, "settings", "unset"]
        if use_local:
            cmd.append("--local")
        cmd.append(setting_name)

        if module.check_mode:
            module.exit_json(
                changed=True, name=setting_name, state=state, local=use_local
            )

        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            module.fail_json(
                msg="Failed to run 'mise settings unset': {0}".format(stderr)
            )

        module.exit_json(
            changed=True,
            name=setting_name,
            state=state,
            local=use_local,
            stdout=stdout,
            stderr=stderr,
            msg="Setting '{0}' has been removed.".format(setting_name),
        )


if __name__ == "__main__":
    main()
