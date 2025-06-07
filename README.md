# Checkmk plugin for Arbiter GNSS clocks

## Description

This Checkmk extension decodes the SNMP response of Arbiter GNSS clocks.

## Setup
- Install the Checkmk *.mkp as normal
- Add the GPS clock as a host, ensure the following settings
    - (required) Set SNMP to v2, set SNMPv2 community string set to public
    - (recommended) Set "Checkmk agent / API integrations" to "No API Integrations / No Checkmk Agent"
- Run service discovery
- Add services you wish to track

## Tested clocks / notes
- Arbiter 1088B
    - May jump to previous GPS epochs on cold startups.  Resolve by manually setting the time via serial prior to GPS antenna attach

## Edits compared to the container
 - `.devcontainer` -> `devcontainer.json`,`Dockerfile` modified to use Checkmk Cloud 2.4.0p3 (see: [this forum post](https://forum.checkmk.com/t/best-ide-configuration-practices-for-checkmk-plug-in-development/50135/12))

# Notes from the repo template

## Development

For the best development experience use [VSCode](https://code.visualstudio.com/) with the [Remote Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension. This maps your workspace into a checkmk docker container giving you access to the python environment and libraries the installed extension has.

## Directories

The following directories in this repo are getting mapped into the Checkmk site.

* `agents`, `checkman`, `checks`, `doc`, `inventory`, `notifications`, `web` are mapped into `local/share/check_mk/`
* `agent_based` is mapped to `local/lib/check_mk/base/plugins/agent_based`
* `nagios_plugins` is mapped to `local/lib/nagios/plugins`
* `bakery` is mapped to `local/lib/check_mk/base/cee/plugins/bakery`
* `temp` is mapped to `local/tmp` for storing precreated agent output
