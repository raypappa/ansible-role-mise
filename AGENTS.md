# AGENTS.md — ansible-role-mise

## What This Is

Ansible role for installing [mise](https://mise.jdx.dev/) (polyglot runtime manager). Role name on Galaxy: `mise`. Includes three custom modules in `library/`: `mise_use`, `mise_install`, `mise_settings`.

## Quick Commands

```bash
# Full test suite (lint + converge + idempotence + verify + destroy)
molecule test

# Just apply role to containers
molecule converge

# Just run verification assertions
molecule verify

# Login to a running container for debugging
molecule login --host ubuntu-noble

# Destroy and recreate containers from scratch
molecule reset
```

## Pre-commit Hooks

Runs automatically on commit. Includes:
- `yamllint` (config: `.yamllint`)
- `ansible-lint` (config: `.ansible-lint`)
- `check-github-workflows`
- trailing whitespace, end-of-file, check-yaml

To run manually: `pre-commit run --all-files`

## Linting Config

**ansible-lint** skips: `yaml[truthy]`, `name[template]`. Excludes `molecule/` and `.github/`.

**yamllint** max line length: 200 (warning). Allows `yes`/`no` as truthy values.

## Testing

Uses Molecule with Docker. Default scenario tests against:
- `ubuntu:noble`
- `debian:bookworm`
- `fedora:latest`

Setup prerequisites:
```bash
pip install -r requirements.txt
ansible-galaxy install -r requirements.yml
```

The `geerlingguy.docker` role is a dependency (pulled via `requirements.yml`).

## Custom Modules

Located in `library/`. When using in playbooks, always pass `executable`:
```yaml
mise_use:
  name: node@22
  executable: "{{ mise_install_path }}"
```

- `mise_use` — installs tools to config (global or local)
- `mise_install` — installs tool versions without adding to config

## CI Workflows

- `molecule.yml` — Linux molecule tests on push/PR
- `windows.yml` — Windows tests on push/PR
- `galaxy.yml` — Publish to Ansible Galaxy on version tags (`v*.*.*`)
