#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2025, Stoney Jackson
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: mise_use
short_description: Install a tool and add the version to mise.toml
version_added: "1.0.0"
description:
    - Installs a tool version and adds it to a mise.toml config file.
    - This is equivalent to running C(mise use) from the command line.
    - By default, this uses the C(mise.toml) in the current directory.
    - Use O(global_config=true) to use the global config file (~/.config/mise/config.toml).
    - Use O(system_config=true) to use the system-wide config file (/etc/mise/config.toml).
    - Use O(path) to specify a specific config file or directory.
    - Use O(env) to create/modify an environment-specific config like .mise.<env>.toml.
options:
    name:
        description:
            - The tool name, optionally with a version suffix and/or tool options.
            - Format: C(backend:tool@version[option=value,...]) or C(tool@version[option=value,...]).
            - If no version is specified, it defaults to C(@latest).
            - Supports backend prefixes (e.g. C(cargo:ripgrep@latest), C(npm:prettier@3)).
            - Supports tool options (e.g. C(ubi:BurntSushi/ripgrep[exe=rg]), C(cargo:ripgrep[features=...] )).
            - The entire string is passed to C(mise use) as-is; mise handles the parsing.
            - Can be a list of tools to install/remove in one go.
        type: raw
        required: true
    state:
        description:
            - Whether the tool should be present in the config or absent.
            - V(present) installs the tool and adds it to the config.
            - V(absent) removes the tool from the config (equivalent to C(mise unuse)).
        type: str
        default: present
        choices: ['present', 'absent']
    global_config:
        description:
            - Use the global config file (~/.config/mise/config.toml) instead of the local one.
        type: bool
        default: false
    system_config:
        description:
            - Use the system-wide config file (/etc/mise/config.toml).
            - Requires root or appropriate permissions to write to C(/etc/mise/config.toml).
        type: bool
        default: false
    path:
        description:
            - Specify a path to a config file or directory.
            - If a directory is specified, mise will look for a config file in that directory.
        type: str
    env:
        description:
            - Create/modify an environment-specific config file like .mise.<env>.toml.
        type: str
    force:
        description:
            - Force reinstall even if already installed.
        type: bool
        default: false
    pin:
        description:
            - Save the resolved concrete version to the config file instead of a fuzzy version.
            - E.g. V(pin=true) with C(node@20) will save C(20.x.y) instead of C(20).
        type: bool
        default: false
    fuzzy:
        description:
            - Save fuzzy version to config file.
            - This is the default behavior unless C(MISE_PIN=1).
            - E.g. C(mise use --fuzzy node@20) will save C(20) as the version.
        type: bool
        default: true
    no_prune:
        description:
            - Do not prune the installed version after removing from config when O(state=absent).
            - By default, mise will prune the installed version if no other configs reference it.
            - Only applies when O(state=absent).
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
    - name: mise documentation for mise use
      link: https://mise.jdx.dev/cli.html#mise-use
      description: Official documentation for the C(mise use) command.
"""

EXAMPLES = r"""
- name: Install node 20 in the current directory's mise.toml
  community.general.mise_use:
    name: node@20

- name: Install python 3.12 globally
  community.general.mise_use:
    name: python@3.12
    global_config: true

- name: Install node 20 system-wide
  community.general.mise_use:
    name: node@20
    system_config: true

- name: Install multiple tools at once
  community.general.mise_use:
    name:
      - node@20
      - python@3.12
      - rust@latest
    global_config: true

- name: Install latest node and pin the exact version
  community.general.mise_use:
    name: node@latest
    pin: true

- name: Install a tool via a backend prefix
  community.general.mise_use:
    name: cargo:ripgrep@latest

- name: Install a tool with backend options
  community.general.mise_use:
    name: "ubi:BurntSushi/ripgrep[exe=rg]"
    global_config: true

- name: Install a Cargo tool with feature flags
  community.general.mise_use:
    name: "cargo:ripgrep[features=+use_jemalloc]"

- name: Install node 20 to a specific config path
  community.general.mise_use:
    name: node@20
    path: /path/to/project

- name: Install node 20 in an environment-specific config
  community.general.mise_use:
    name: node@20
    env: staging

- name: Remove python from the local mise.toml
  community.general.mise_use:
    name: python
    state: absent

- name: Remove multiple tools from the config
  community.general.mise_use:
    name:
      - node
      - python
    state: absent
"""

RETURN = r"""
name:
    description: The tool name(s) as provided (string or list).
    type: raw
    returned: always
version:
    description: The version string(s) (e.g. C(20), C(latest)).
    type: raw
    returned: always
state:
    description: The desired state (V(present) or V(absent)).
    type: str
    returned: always
global_config:
    description: Whether the global config was used.
    type: bool
    returned: always
system_config:
    description: Whether the system config was used.
    type: bool
    returned: always
changed:
    description: Whether the module made changes.
    type: bool
    returned: always
tools:
    description: List of individual tool results when name is a list.
    type: list
    elements: dict
    returned: when name is a list
"""

import os
import json

from ansible.module_utils.basic import AnsibleModule


def _find_mise(module):
    """Locate the mise executable."""
    exe = module.params.get("executable")
    if exe and os.path.isfile(exe) and os.access(exe, os.X_OK):
        return exe

    path = module.get_bin_path("mise", required=False)
    if path:
        return path

    module.fail_json(
        msg="mise executable not found. Install mise or specify the 'executable' parameter."
    )


def _get_current_tools(mise_path, scope_flag, module, cwd=None):
    """Get the current tools from mise ls --json."""
    cmd = [mise_path, "ls", "--json"]
    if scope_flag in ("--global", "--system"):
        cmd.append(scope_flag)
    # --path/--env scopes have no `mise ls` flag; cwd makes mise resolve
    # the config file at that location instead.

    rc, stdout, stderr = module.run_command(cmd, cwd=cwd)
    if rc != 0:
        module.fail_json(msg="Failed to list mise tools: {0}".format(stderr))

    try:
        return json.loads(stdout) if stdout.strip() else {}
    except (ValueError, KeyError):
        return {}


def _tool_is_in_config(tools, tool_name):
    """Check if a tool is currently configured (has a source entry)."""
    if tool_name not in tools:
        return False
    entries = tools[tool_name]
    for entry in entries:
        source = entry.get("source", {})
        if source.get("type") in ("mise.toml", "tool-versions"):
            return True
    return False


def _parse_tool_name(name_str):
    """Parse tool name, version, and options from mise tool string.

    Supports formats:
        - tool
        - tool@version
        - backend:tool@version
        - tool[option=value,...]
        - tool@version[option=value,...]
        - backend:tool@version[option=value,...]

    Returns (tool_name, version, options_str) where options_str includes brackets.
    """
    # Extract options if present (everything from first '[' to end)
    options_str = ""
    if "[" in name_str:
        bracket_idx = name_str.index("[")
        options_str = name_str[bracket_idx:]
        name_str = name_str[:bracket_idx]

    # Extract version if present
    if "@" in name_str:
        tool_name, version = name_str.split("@", 1)
    else:
        tool_name = name_str
        version = "latest"

    return tool_name, version, options_str


def _run_mise_use(
    module, mise_path, name, use_global, use_system, path, env, force, pin, fuzzy
):
    cwd = path if (path and not use_global and not use_system) else None
    """Run mise use for a single tool and return result dict."""
    tool_name, version, options_str = _parse_tool_name(name)

    # Determine scope flag
    scope_flag = None
    if use_global:
        scope_flag = "--global"
    elif use_system:
        scope_flag = "--system"
    elif path:
        scope_flag = "--path"
    elif env:
        scope_flag = "--env"

    # Check current state
    current_tools = _get_current_tools(mise_path, scope_flag, module, cwd=cwd)
    is_in_config = _tool_is_in_config(current_tools, tool_name)

    if is_in_config and not force:
        return {
            "changed": False,
            "name": tool_name,
            "version": version,
            "msg": "Tool '{0}' is already in the mise config.".format(tool_name),
        }

    # Build the mise use command
    # Pass the full name string (including options) to mise
    cmd = [mise_path, "use"]
    if use_global:
        cmd.append("--global")
    if use_system:
        cmd.append("--system")
    if path:
        cmd.extend(["--path", path])
    if env:
        cmd.extend(["--env", env])
    if force:
        cmd.append("--force")
    if pin:
        cmd.append("--pin")
    if fuzzy and not pin:
        cmd.append("--fuzzy")
    cmd.append(name)

    if module.check_mode:
        return {
            "changed": True,
            "name": tool_name,
            "version": version,
            "msg": "Tool '{0}' would be installed.".format(tool_name),
        }

    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        module.fail_json(
            msg="Failed to run 'mise use' for '{0}': {1}".format(name, stderr)
        )

    return {
        "changed": True,
        "name": tool_name,
        "version": version,
        "stdout": stdout,
        "stderr": stderr,
        "msg": "Tool '{0}@{1}' has been added to the mise config.".format(
            tool_name, version
        ),
    }


def _run_mise_unuse(
    module, mise_path, name, use_global, use_system, path, env, no_prune
):
    cwd = path if (path and not use_global and not use_system) else None
    """Run mise unuse for a single tool and return result dict."""
    tool_name, version, options_str = _parse_tool_name(name)

    # Determine scope flag
    scope_flag = None
    if use_global:
        scope_flag = "--global"
    elif use_system:
        scope_flag = "--system"
    elif path:
        scope_flag = "--path"
    elif env:
        scope_flag = "--env"

    # Check current state
    current_tools = _get_current_tools(mise_path, scope_flag, module, cwd=cwd)
    is_in_config = _tool_is_in_config(current_tools, tool_name)

    if not is_in_config:
        return {
            "changed": False,
            "name": tool_name,
            "version": version,
            "msg": "Tool '{0}' is not in the mise config.".format(tool_name),
        }

    # Build the mise unuse command
    cmd = [mise_path, "unuse"]
    if use_global:
        cmd.append("--global")
    if use_system:
        cmd.append("--system")
    if path:
        cmd.extend(["--path", path])
    if env:
        cmd.extend(["--env", env])
    if no_prune:
        cmd.append("--no-prune")
    cmd.append(name)

    if module.check_mode:
        return {
            "changed": True,
            "name": tool_name,
            "version": version,
            "msg": "Tool '{0}' would be removed.".format(tool_name),
        }

    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        module.fail_json(
            msg="Failed to run 'mise unuse' for '{0}': {1}".format(name, stderr)
        )

    return {
        "changed": True,
        "name": tool_name,
        "version": version,
        "stdout": stdout,
        "stderr": stderr,
        "msg": "Tool '{0}' has been removed from the mise config.".format(tool_name),
    }


def main():
    spec = dict(
        name=dict(type="raw", required=True),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        global_config=dict(type="bool", default=False),
        system_config=dict(type="bool", default=False),
        path=dict(type="str"),
        env=dict(type="str"),
        force=dict(type="bool", default=False),
        pin=dict(type="bool", default=False),
        fuzzy=dict(type="bool", default=True),
        no_prune=dict(type="bool", default=False),
        executable=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=spec,
        mutually_exclusive=[
            ["global_config", "system_config", "path", "env"],
        ],
        supports_check_mode=True,
    )

    name = module.params["name"]
    state = module.params["state"]
    use_global = module.params["global_config"]
    use_system = module.params["system_config"]
    path = module.params["path"]
    env = module.params["env"]
    force = module.params["force"]
    pin = module.params["pin"]
    fuzzy = module.params["fuzzy"]
    no_prune = module.params["no_prune"]

    mise_path = _find_mise(module)

    # Normalize name to list
    if isinstance(name, str):
        names = [name]
    else:
        names = list(name)

    # Process all tools
    results = []
    any_changed = False

    for tool in names:
        if state == "present":
            result = _run_mise_use(
                module,
                mise_path,
                tool,
                use_global,
                use_system,
                path,
                env,
                force,
                pin,
                fuzzy,
            )
        else:
            result = _run_mise_unuse(
                module, mise_path, tool, use_global, use_system, path, env, no_prune
            )
        results.append(result)
        if result.get("changed"):
            any_changed = True

    # Build final result
    output = {
        "changed": any_changed,
        "state": state,
        "global_config": use_global,
        "system_config": use_system,
    }

    if len(names) == 1:
        # Single tool: return flat result for backward compatibility
        output.update(results[0])
    else:
        # Multiple tools: return structured results
        output["name"] = names
        output["version"] = [r.get("version") for r in results]
        output["tools"] = results
        output["msg"] = "Processed {0} tools.".format(len(names))

    module.exit_json(**output)


if __name__ == "__main__":
    main()
