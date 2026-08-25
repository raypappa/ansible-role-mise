# ansible-role-mise

An Ansible role to install and configure [mise](https://mise.jdx.dev/) (mise-en-place) — a polyglot runtime manager that replaces tools like nvm, pyenv, rbenv, goenv, and more.

## Features

- **Multi-platform**: Linux (Debian, Ubuntu, Fedora, RHEL, Alpine, Amazon Linux) and Windows (10/11, Server 2019/2022)
- **Multiple install methods**: Auto-detect or explicitly choose from curl, apt, dnf, brew, snap, npm, cargo, apk, scoop, winget, manual
- **Global or local install**: System-wide or per-user installation
- **Shell activation**: Automatic setup for bash, zsh, fish, PowerShell
- **Configuration**: Apply mise settings, environment variables, and trust configs
- **Autocompletion**: Install shell completion scripts
- **Custom modules**: `mise_use` and `mise_install` for managing tools in your playbooks
- **Idempotent**: Safe to run multiple times

## Requirements

- Ansible >= 2.14
- For curl install: `curl` on the target host
- For scoop install: `scoop` on Windows
- For winget install: `winget` on Windows

## Role Variables

### Defaults

```yaml
# Installation method (auto, curl, apt, dnf, brew, snap, npm, cargo, apk, scoop, winget, manual)
mise_install_method: auto

# mise version (empty = latest)
mise_version: ""

# Binary install path (auto-detected if empty)
mise_install_path: ""

# Install scope: "global" or "local"
mise_install_scope: local

# Target user for local installs
mise_user: "{{ ansible_user_id }}"

# Shell for activation: bash, zsh, fish, powershell (auto-detected if "auto")
mise_shell: auto

# Whether to activate mise in shell RC
mise_activate_shell: true

# mise settings to configure
mise_settings: {}

# Environment variables
mise_env: {}

# Trust all config files
mise_trust_all_configs: false

# Install autocompletion
mise_install_completion: false
```

## Installation Methods

| Method | Platforms | Notes |
|--------|-----------|-------|
| `auto` | All | Auto-detects best method per OS |
| `curl` | Linux/macOS | Uses `mise.run` installer (recommended) |
| `apt` | Debian/Ubuntu | Uses official APT repository |
| `dnf` | Fedora/RHEL | Uses COPR repository |
| `brew` | macOS/Linux | Via Homebrew |
| `snap` | Linux | Via Snap Store |
| `npm` | All | Via npm global install |
| `cargo` | All | Build from source |
| `apk` | Alpine | Community package |
| `scoop` | Windows | Recommended for Windows |
| `winget` | Windows | Windows Package Manager |
| `manual` | Windows | Direct GitHub release download |

## Usage

### Basic Installation

```yaml
- hosts: all
  roles:
    - role: ansible-role-mise
```

### Install with Specific Version

```yaml
- hosts: all
  roles:
    - role: ansible-role-mise
      vars:
        mise_version: "2025.12.0"
```

### Global Install

```yaml
- hosts: all
  become: true
  roles:
    - role: ansible-role-mise
      vars:
        mise_install_scope: global
```

### Local Install with Shell Activation

```yaml
- hosts: workstation
  roles:
    - role: ansible-role-mise
      vars:
        mise_install_scope: local
        mise_shell: zsh
        mise_activate_shell: true
        mise_install_completion: true
```

### Windows with scoop

```yaml
- hosts: windows
  roles:
    - role: ansible-role-mise
      vars:
        mise_install_method: scoop
        mise_shell: powershell
        mise_activate_shell: true
```

### Windows with winget

```yaml
- hosts: windows
  roles:
    - role: ansible-role-mise
      vars:
        mise_install_method: winget
```

### With Settings and Environment Variables

```yaml
- hosts: all
  roles:
    - role: ansible-role-mise
      vars:
        mise_settings:
          auto_update: true
          trusted_config_paths:
            - "/"
        mise_env:
          MISE_JOBS: "4"
```

## Installing Tools

After installing mise, use the `mise_use` module to install tools:

```yaml
- hosts: all
  become: true
  roles:
    - role: ansible-role-mise

  tasks:
    - name: Install node and python globally
      mise_use:
        name:
          - node@22
          - python@3.12
        global_config: true
        executable: "{{ mise_install_path }}"

    - name: Install ripgrep
      mise_use:
        name: ripgrep@latest
        global_config: true
        executable: "{{ mise_install_path }}"

    - name: Remove node from config
      mise_use:
        name: node
        state: absent
        global_config: true
        executable: "{{ mise_install_path }}"
```

See the `mise_use` module documentation for all options.

## Managing Tool Versions

Use `mise_install` to install tool versions without adding to config:

```yaml
- name: Install specific rust version
  mise_install:
    name: rust@1.75.0
    executable: "{{ mise_install_path }}"

- name: Install latest rust
  mise_install:
    name: rust@latest
    executable: "{{ mise_install_path }}"

- name: Uninstall a version
  mise_install:
    name: rust@1.75.0
    state: absent
    executable: "{{ mise_install_path }}"
```

## Configuring mise Settings

Use `mise_settings` to manage mise configuration:

```yaml
- name: Enable auto-update
  mise_settings:
    name: auto_update
    value: true
    executable: "{{ mise_install_path }}"

- name: Add trusted config path
  mise_settings:
    name: trusted_config_paths
    value: "/"
    executable: "{{ mise_install_path }}"

- name: Get current setting value
  mise_settings:
    name: auto_update
    state: get
    executable: "{{ mise_install_path }}"
  register: result

- name: Remove a setting
  mise_settings:
    name: auto_update
    state: absent
    executable: "{{ mise_install_path }}"
```

## CI/CD

### GitHub Actions

This role includes GitHub Actions workflows for automated testing and publishing:

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `molecule.yml` | Push to main, PRs, weekly schedule | Linux molecule tests (Ubuntu, Debian, Fedora) |
| `windows.yml` | Push to main, PRs | Windows tests (scoop, winget, manual) |
| `galaxy.yml` | Version tags (`v*.*.*`) | Publish to Ansible Galaxy |

### Testing on Forks

The CI workflows run on pull requests. Forks will need:

1. No special secrets for Linux tests (runs with Docker)
2. Windows tests run on `windows-latest` GitHub runner

### Publishing to Galaxy

1. Create a version tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. Set up Galaxy API key in GitHub secrets:
   - Go to repository Settings → Secrets and variables → Actions
   - Add `GALAXY_API_KEY` with your Ansible Galaxy API token

3. The role will be automatically published to:
   [https://galaxy.ansible.com/stoney/mise](https://galaxy.ansible.com/stoney/mise)

## Testing

### Prerequisites

```bash
pip install -r requirements.txt
ansible-galaxy install -r requirements.yml
```

### Run Molecule Tests

```bash
# Default scenario (Linux)
molecule test

# Run only converge
molecule converge

# Run only verify
molecule verify

# Destroy and recreate
molecule reset

# Login to container for debugging
molecule login --host ubuntu-noble
```

### Windows Testing

```bash
# Windows scenario (requires Windows Docker image or remote Windows host)
molecule test -s windows
```

## Example Playbook

```yaml
---
- name: Set up development environment with mise
  hosts: dev_workstations
  become: true
  vars:
    mise_install_scope: local
    mise_shell: bash
    mise_activate_shell: true
    mise_install_completion: true
    mise_settings:
      auto_update: true
    mise_env:
      MISE_JOBS: "4"

  roles:
    - role: ansible-role-mise

  tasks:
    - name: Install development tools
      mise_use:
        name:
          - node@22
          - python@3.12
          - golang@1.22
          - rust@latest
          - jq@latest
          - ripgrep@latest
          - fd@latest
        executable: "{{ mise_install_path }}"
```

## License

MIT

## Author

stoney
