# Checkmk plugin for Arbiter GNSS clocks

## Description

This Checkmk extension decodes the SNMP response of Arbiter GNSS clocks.

## Setup
- Install the Checkmk *.mkp as normal
- Add the GPS clock as a host, ensure the following settings
    - (required) Set SNMP to v2, set SNMPv2 community string set to public
    - (recommended) Set "Checkmk agent / API integrations" to "No API Integrations / No Checkmk Agent"
- In Setup > Agent > SNMP Settings > Hosts without system description OID, add a rule to match the hostname/folder/label (as needed) of your clocks
- Run service discovery
- Add services you wish to track

## Tested clocks / notes
- Arbiter 1088B
    - May jump to previous GPS epochs on cold startups.  Resolve by manually setting the time via serial prior to GPS antenna attach

_If you see any problems with specific clocks or unenumerated data, please raise an issue!_

## Debugging
- The VS Code Run/Debug launchers are bound to a host named "arbiter" - you may need to create your clock with that name or update the run/debug config
- THis is configured by the `CHECKHOST` variable in `.env`

## Reference
- Arbiter MIBs: https://www.arbiter.com/files/software/ntp_ptp/ARBITER-ALL-MIB.mib
