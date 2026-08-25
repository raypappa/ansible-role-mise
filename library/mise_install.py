#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025, Stoney Jackson
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: mise_install
short_description: Install a mise tool version
version_added: "1.0.0"
description:
    - Installs a tool version to C(~/.local/share/mise/installs/<TOOL>/<VERSION>).
    - This is equivalent to running C(mise install) from the command line.
    - Installing alone will not activate the tools so they won't be in PATH.
    - To install and activate in one command, use M(community.general.mise_use) instead.
options:
    name:
        description:
            - The tool name with optional version suffix (e.g. C(node@20.0.0), C(node@20)).
            - If no version is specified, it will install the version from the config.
            - Supports backend prefixes (e.g. C(cargo:ripgrep@latest)).
        type: str
        required: true
    state:
        description:
            - Whether the tool should be installed or absent.
            - V(present) installs the tool.
            - V(absent) uninstalls the tool (equivalent to C(mise uninstall)).
        type: str
        default: present
        choices: ['present', 'absent']
    force:
        description:
            - Force reinstall even if already installed.
        type: bool
        default: false
    all_versions:
        description:
            - Uninstall all installed versions of the tool when O(state=absent).
            - Only applies when O(state=absent).
        type: bool
        default: false
    jobs:
        description:
            - Number of jobs to run in parallel for installation.
            - Values below 1 are treated as 1.
        type: int
        default: 4
    shared:
        description:
            - Install tool(s) to a shared directory instead of the default install location.
            - May require elevated permissions depending on the path.
        type: str
    system:
        description:
            - Install tool(s) to the system-wide shared directory.
            - Installs to /usr/local/share/mise/installs (or MISE_SYSTEM_DATA_DIR/installs).
            - May require elevated permissions.
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
    - name: mise documentation for mise install
      link: https://mise.jdx.dev/cli.html#mise-install
      description: Official documentation for the C(mise install) command.
"""

EXAMPLES = r"""
- name: Install node 20.0.0
  community.general.mise_install:
    name: node@20.0.0

- name: Install a specific node version with force
  community.general.mise_install:
    name: node@20.0.0
    force: true

- name: Install node version from mise.toml config
  community.general.mise_install:
    name: node

- name: Install latest ripgrep via cargo backend
  community.general.mise_install:
    name: cargo:ripgrep@latest

- name: Uninstall a specific node version
  community.general.mise_install:
    name: node@20.0.0
    state: absent

- name: Uninstall all node versions
  community.general.mise_install:
    name: node
    state: absent
    all_versions: true
"""

RETURN = r"""
name:
    description: The tool name as provided.
    type: str
    returned: always
version:
    description: The version string if provided.
    type: str
    returned: always
state:
    description: The desired state (V(present) or V(absent)).
    type: str
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


def _is_installed(mise_path, tool_name, module):
    """Check if a tool is installed."""
    cmd = [mise_path, "ls", "--json", "--installed", tool_name]

    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        return False

    try:
        data = json.loads(stdout) if stdout.strip() else {}
        # mise ls --json <tool> returns a list of version entries
        if isinstance(data, list):
            return len(data) > 0
        # mise ls --json returns a dict keyed by tool name
        if isinstance(data, dict):
            return tool_name in data and len(data[tool_name]) > 0
        return False
    except (ValueError, KeyError):
        return False


def main():
    spec = dict(
        name=dict(type="str", required=True),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        force=dict(type="bool", default=False),
        all_versions=dict(type="bool", default=False),
        jobs=dict(type="int", default=4),
        shared=dict(type="str"),
        system=dict(type="bool", default=False),
        executable=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    force = module.params["force"]
    all_versions = module.params["all_versions"]
    jobs = module.params["jobs"]
    shared = module.params["shared"]
    system = module.params["system"]

    mise_path = _find_mise(module)

    # Parse tool name and version from "name@version" format
    if "@" in name:
        tool_name, version = name.split("@", 1)
    else:
        tool_name = name
        version = None

    if state == "present":
        installed = _is_installed(mise_path, tool_name, module)
        if installed and not force:
            module.exit_json(
                changed=False,
                name=tool_name,
                version=version,
                state=state,
                msg="Tool '{0}' is already installed.".format(tool_name),
            )

        # Build the mise install command
        cmd = [mise_path, "install"]
        if force:
            cmd.append("--force")
        if jobs > 1:
            cmd.extend(["--jobs", str(jobs)])
        if shared:
            cmd.extend(["--shared", shared])
        if system:
            cmd.append("--system")
        cmd.append(name)

        if module.check_mode:
            module.exit_json(changed=True, name=tool_name, version=version, state=state)

        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            module.fail_json(msg="Failed to run 'mise install': {0}".format(stderr))

        module.exit_json(
            changed=True,
            name=tool_name,
            version=version,
            state=state,
            stdout=stdout,
            stderr=stderr,
            msg="Tool '{0}' has been installed.".format(name),
        )

    elif state == "absent":
        installed = _is_installed(mise_path, tool_name, module)
        if not installed:
            module.exit_json(
                changed=False,
                name=tool_name,
                version=version,
                state=state,
                msg="Tool '{0}' is not installed.".format(tool_name),
            )

        # Build the mise uninstall command
        cmd = [mise_path, "uninstall"]
        if all_versions:
            cmd.append("--all")
        cmd.append(name)

        if module.check_mode:
            module.exit_json(changed=True, name=tool_name, version=version, state=state)

        rc, stdout, stderr = module.run_command(cmd)
        if rc != 0:
            module.fail_json(msg="Failed to run 'mise uninstall': {0}".format(stderr))

        module.exit_json(
            changed=True,
            name=tool_name,
            version=version,
            state=state,
            stdout=stdout,
            stderr=stderr,
            msg="Tool '{0}' has been uninstalled.".format(name),
        )


if __name__ == "__main__":
    main()
