#!/usr/bin/env python3

import datetime
import time
from typing import Union
from cmk.agent_based.v2 import (  # type: ignore
    CheckPlugin,
    CheckResult,
    check_levels,
    exists,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    # StringTable,
)

_METRIC_SANITY_LEVELS = {
    "ntpSysOffset": (0, 1),
    "ntpSysFreq": (0, 1),
    "ntpSysSysJitter": (0, 100),
    "ntpSysClkJitter": (0, 100),
    "ntpSysClkWander": (0, 100),
    "ntpSysRootDelay": (0, 100),
    "ntpSysRootDispersion": (0, 10000),
    "ntpSysStratum": (0, 2),
    "ntpSysPrecision": (0, 1),
}

# fractional time algorithm from https://github.com/cf-natali/ntplib/blob/master/ntplib.py
# retrieved 2025-06-07
_SYSTEM_EPOCH = datetime.datetime(*time.gmtime(0)[0:3], tzinfo=datetime.timezone.utc)
_NTP_EPOCH = datetime.datetime(1900, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
_NTP_DELTA = int((_SYSTEM_EPOCH - _NTP_EPOCH).total_seconds())


def ntp_fract_composite(integ: int, frac: int, bits: int = 32) -> float:
    """Return a timestamp from an integral and fractional part.

    Parameters:
    integ -- integral part
    frac  -- fractional part
    bits  -- number of bits of the fractional part

    Returns:
    timestamp
    """
    return integ + float(frac) / 2**bits


def parse_arbiter_ntp_hex_time(string_hex: str) -> datetime.datetime:
    fract_split = string_hex.split(".")
    whole = int(fract_split[0], 16)
    fract = int(fract_split[1], 16)
    return datetime.datetime.fromtimestamp(
        ntp_fract_composite(whole, fract, 16) - _NTP_DELTA
    )


def parse_arbiter_gnss(
    string_table: list[list[str]],
) -> dict[str, Union[str, int, float, datetime.datetime]]:
    """
    .1.3.6.1.4.1.39849.3.1.1.0 NTP Time Server --> ARBITER-ALL-MIB::ntpSysString.0
    .1.3.6.1.4.1.39849.3.1.2.0 eb4ada9f.68554933 --> ARBITER-ALL-MIB::ntpSysClock.0
    .1.3.6.1.4.1.39849.3.1.3.0 Feb  3 2025  0:03:11.407, peer=64326 --> ARBITER-ALL-MIB::ntpSysClockDateTime.0
    .1.3.6.1.4.1.39849.3.1.4.0 0 --> ARBITER-ALL-MIB::ntpSysOffset.0
    .1.3.6.1.4.1.39849.3.1.5.0 0 --> ARBITER-ALL-MIB::ntpSysFreq.0
    .1.3.6.1.4.1.39849.3.1.6.0 0 --> ARBITER-ALL-MIB::ntpSysSysJitter.0
    .1.3.6.1.4.1.39849.3.1.7.0 15 --> ARBITER-ALL-MIB::ntpSysClkJitter.0
    .1.3.6.1.4.1.39849.3.1.8.0 0 --> ARBITER-ALL-MIB::ntpSysClkWander.0
    .1.3.6.1.4.1.39849.3.1.9.0 0 --> ARBITER-ALL-MIB::ntpSysRootDelay.0
    .1.3.6.1.4.1.39849.3.1.10.0 11601 --> ARBITER-ALL-MIB::ntpSysRootDispersion.0
    .1.3.6.1.4.1.39849.3.1.11.0 0 --> ARBITER-ALL-MIB::ntpSysLeap.0
    .1.3.6.1.4.1.39849.3.1.12.0 1 --> ARBITER-ALL-MIB::ntpSysStratum.0
    .1.3.6.1.4.1.39849.3.1.13.0 -16 --> ARBITER-ALL-MIB::ntpSysPrecision.0
    .1.3.6.1.4.1.39849.3.1.14.0 eb4ada72.747d467f --> ARBITER-ALL-MIB::ntpSysRefTime.0
    """
    "[['NTP Time Server'], ['eb4ae858.b35c7442'], ['Feb  3 2025  1:01:44.700, peer=64326'], ['0'], ['0'], ['0'], ['15'], ['0'], ['0'], ['11511'], ['0'], ['1'], ['-16'], ['eb4ae832.747cb4a1']]"
    # print(string_table)
    clock_item: dict[str, Union[str, int, float, datetime.datetime]] = {}
    clock_item["ntpSysString"] = string_table[0][0]
    clock_item["ntpSysClock"] = parse_arbiter_ntp_hex_time(string_table[1][0])
    clock_item["ntpSysClockDateTime"] = string_table[2][0]
    clock_item["ntpSysOffset"] = int(string_table[3][0])
    clock_item["ntpSysFreq"] = int(string_table[4][0])
    clock_item["ntpSysSysJitter"] = int(string_table[5][0])
    clock_item["ntpSysClkJitter"] = int(string_table[6][0])
    clock_item["ntpSysClkWander"] = int(string_table[7][0])
    clock_item["ntpSysRootDelay"] = int(string_table[8][0])
    clock_item["ntpSysRootDispersion"] = int(string_table[9][0])
    clock_item["ntpSysLeap"] = string_table[10][0]
    clock_item["ntpSysStratum"] = int(string_table[11][0])
    clock_item["ntpSysPrecision"] = int(string_table[12][0])
    clock_item["ntpSysRefTime"] = parse_arbiter_ntp_hex_time(string_table[13][0])
    return clock_item


def discover_arbiter_gnss(
    section: dict[str, Union[str, int, float, datetime.datetime]],
) -> DiscoveryResult:
    for field in section:
        yield Service(item=field)


def check_arbiter_gnss(
    item: str, section: dict[str, Union[str, int, float, datetime.datetime]]
) -> CheckResult:
    print("CHK", item, section.get(item))
    if item in (
        "ntpSysString",
        "ntpSysClockDateTime",
        "ntpSysLeap",
        "ntpSysClock",
        "ntpSysRefTime",
    ):

        field_val = section.get(item)
        print("Result ->", field_val)
        yield Result(state=State.OK, summary=str(field_val))
    elif item == "ntpSysPrecision":
        ntpSysPrecision = section.get(item)
        assert isinstance(ntpSysPrecision, int)
        ntpSysPrecision_us = (2**ntpSysPrecision) * 1000000
        print("Metric ->", ntpSysPrecision_us)
        yield from check_levels(
            metric_name=item,
            value=ntpSysPrecision_us,
            boundaries=_METRIC_SANITY_LEVELS[item],
        )
    elif item in (
        "ntpSysOffset",
        "ntpSysFreq",
        "ntpSysSysJitter",
        "ntpSysClkJitter",
        "ntpSysClkWander",
        "ntpSysRootDelay",
        "ntpSysRootDispersion",
        "ntpSysStratum",
    ):
        clk_stat_value = section.get(item)
        assert isinstance(clk_stat_value, (int, float))
        print("Metric ->", clk_stat_value)
        yield from check_levels(
            metric_name=item,
            value=clk_stat_value,
            boundaries=_METRIC_SANITY_LEVELS[item],
        )
    else:
        raise ValueError(f"Encountered item {item} not present in section {section}")


snmp_section_arbiter_gnss = SimpleSNMPSection(
    name="arbiter_gnss",
    # service_name = "Arbiter GNSS Clock",
    parse_function=parse_arbiter_gnss,
    detect=exists(".1.3.6.1.4.1.39849.1.1.1.0"),
    fetch=SNMPTree(base=".1.3.6.1.4.1.39849", oids=["3"]),
)

check_plugin_arbiter_gnss = CheckPlugin(
    name="arbiter_gnss",
    sections=["arbiter_gnss"],
    service_name="Arbiter %s",
    discovery_function=discover_arbiter_gnss,
    check_function=check_arbiter_gnss,
)
