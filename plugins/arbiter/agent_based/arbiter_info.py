#!/usr/bin/env python3

import datetime
from enum import IntEnum
import functools
import time
from typing import Callable, NamedTuple, Union
from cmk.agent_based.v2 import (  # type: ignore
    CheckPlugin,
    CheckResult,
    check_levels,
    DiscoveryResult,
    exists,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    # StringTable,
)


def _render_unit(value: float, unit: str) -> str:
    return f"{value} {unit}"


ArbiterMetricInfo = NamedTuple(
    "ArbiterMetricInfo",
    (
        ("levels_low", tuple[str, tuple[float, float]] | None),
        ("levels_high", tuple[str, tuple[float, float]] | None),
        ("render", Callable[[float], str] | None),
        ("scaler", float | None),
        ("twopow", bool),
    ),
)


class ArbiterServiceType(IntEnum):
    String = 0
    Number = 1
    Date = 2
    Leap = 3


ArbiterServiceMap = NamedTuple(
    "ArbiterServiceMap",
    (
        ("id", str),
        ("type", ArbiterServiceType),
        ("discovery", bool),
        ("metric", ArbiterMetricInfo | None),
    ),
)


class ArbiterServiceKNMap:
    def __init__(self, init: dict[str, ArbiterServiceMap] = {}) -> None:
        self._dict_n1: dict[str, ArbiterServiceMap] = init
        self._map_n2: dict[str, str] = {}
        if init:
            for k, v in init.items():
                self._map_n2[v.id] = k

    def n1_to_n2(self, name1: str) -> str:
        return self._dict_n1[name1].id

    def n2_to_n1(self, name2: str) -> str:
        return self._map_n2[name2]

    def retrieve_n1(self, name1: str) -> ArbiterServiceMap:
        return self._dict_n1[name1]

    def retrieve_n2(self, name2: str) -> ArbiterServiceMap:
        return self._dict_n1[self._map_n2[name2]]

    def put(self, name1: str, name2: str, value: ArbiterServiceMap):
        self._dict_n1[name1] = value
        self._map_n2[name2] = name1


SERVICE_MAP: ArbiterServiceKNMap = ArbiterServiceKNMap(
    {
        "NTP System String": ArbiterServiceMap(
            "ntpSysString", ArbiterServiceType.String, True, None
        ),
        "NTP System Clock": ArbiterServiceMap(
            "ntpSysClock", ArbiterServiceType.Date, True, None
        ),
        "NTP System Clock - Text": ArbiterServiceMap(
            "ntpSysClockDateTime", ArbiterServiceType.String, False, None
        ),
        "NTP Leap Second Info": ArbiterServiceMap(
            "ntpSysLeap", ArbiterServiceType.Leap, True, None
        ),
        "NTP Reference Time": ArbiterServiceMap(
            "ntpSysRefTime", ArbiterServiceType.Date, True, None
        ),
        "NTP System Offset": ArbiterServiceMap(
            "ntpSysOffset",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                None, ("fixed", (0.5, 1.0)), render.time_offset, None, False
            ),
        ),
        "NTP System Frequency": ArbiterServiceMap(
            "ntpSysFreq",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                None,
                ("fixed", (1, 2)),
                functools.partial(_render_unit, unit="PPM"),
                None,
                False,
            ),
        ),
        "NTP System Jitter": ArbiterServiceMap(
            "ntpSysSysJitter",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                ("fixed", (-100, -50)),
                ("fixed", (50, 100)),
                render.time_offset,
                None,
                False,
            ),
        ),
        "NTP Clock Jitter": ArbiterServiceMap(
            "ntpSysClkJitter",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                ("fixed", (-100, -50)),
                ("fixed", (50, 100)),
                render.time_offset,
                None,
                False,
            ),
        ),
        "NTP Clock Wander": ArbiterServiceMap(
            "ntpSysClkWander",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                ("fixed", (-100, -50)),
                ("fixed", (50, 100)),
                render.time_offset,
                None,
                False,
            ),
        ),
        "NTP Root Delay": ArbiterServiceMap(
            "ntpSysRootDelay",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                None,
                ("fixed", (50, 100)),
                render.time_offset,
                0.000001,
                False,
            ),
        ),
        "NTP Root Dispersion": ArbiterServiceMap(
            "ntpSysRootDispersion",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                None, ("fixed", (0.025, 0.05)), render.time_offset, 0.000001, False
            ),
        ),
        "NTP Stratum": ArbiterServiceMap(
            "ntpSysStratum",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(None, ("fixed", (2, 3)), None, None, False),
        ),
        "NTP System Precision": ArbiterServiceMap(
            "ntpSysPrecision",
            ArbiterServiceType.Number,
            True,
            ArbiterMetricInfo(
                None, ("fixed", (500, 1000)), render.time_offset, None, True
            ),
        ),
    }
)


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
        ntp_fract_composite(whole, fract) - _NTP_DELTA
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
    clock_item["ntpSysLeap"] = int(string_table[10][0])
    clock_item["ntpSysStratum"] = int(string_table[11][0])
    clock_item["ntpSysPrecision"] = int(string_table[12][0])
    clock_item["ntpSysRefTime"] = parse_arbiter_ntp_hex_time(string_table[13][0])
    keys = list(clock_item.keys())
    for key in keys:
        value = clock_item.pop(key)
        clock_item[SERVICE_MAP.n2_to_n1(key)] = value

    return clock_item


def discover_arbiter_gnss(
    section: dict[str, Union[str, int, float, datetime.datetime]],
) -> DiscoveryResult:
    for item in section:
        if SERVICE_MAP.retrieve_n1(item).discovery:
            yield Service(item=item)


def check_arbiter_gnss(
    item: str, section: dict[str, Union[str, int, float, datetime.datetime]]
) -> CheckResult:
    service_map: ArbiterServiceMap = SERVICE_MAP.retrieve_n1(item)
    match service_map.type:
        case ArbiterServiceType.String:
            service_value = section.get(item)
            yield Result(state=State.OK, summary=str(service_value))
        case ArbiterServiceType.Number:
            metric_info = service_map.metric
            assert isinstance(metric_info, ArbiterMetricInfo)
            metric_value_raw = section.get(item)
            assert isinstance(metric_value_raw, int | float)
            metric_value_scaled = metric_value_raw
            if metric_info.twopow:
                metric_value_scaled = 2**metric_value_scaled
            if metric_info.scaler:
                metric_value_scaled = metric_value_scaled * metric_info.scaler

            yield from check_levels(
                metric_name=service_map.id,
                label=item,
                value=metric_value_scaled,
                render_func=metric_info.render,
                levels_lower=metric_info.levels_low,  # type: ignore
                levels_upper=metric_info.levels_high,  # type: ignore
            )
        case ArbiterServiceType.Date:
            date_value = section.get(item)
            assert isinstance(date_value, datetime.datetime)
            yield from check_levels(
                label=item,
                value=date_value.timestamp(),
                render_func=render.datetime,
            )
            ntpSysClockDateTime_name = SERVICE_MAP.n2_to_n1("ntpSysClockDateTime")
            if service_map.id == "ntpSysClock" and ntpSysClockDateTime_name in section:
                yield Result(
                    state=State.OK,
                    summary=f"Clock text: {section.get(ntpSysClockDateTime_name)}",
                )
        case ArbiterServiceType.Leap:
            leap_value = section.get(item)
            assert isinstance(leap_value, int)
            leap_metric: int | None = None
            match leap_value:
                case 0b00:
                    leap_state = State.OK
                    leap_summary = "No leap second is expected"
                    leap_metric = 0
                case 0b01:
                    leap_state = State.WARN
                    leap_summary = "Forward leap second is expected"
                    leap_metric = 1
                case 0b10:
                    leap_state = State.WARN
                    leap_summary = "Reverse leap second is expected"
                    leap_metric = -1
                case 0b11:
                    leap_state = State.CRIT
                    leap_summary = "Clock is unsynchronized"
                case _:
                    leap_state = State.UNKNOWN
                    leap_summary = "Unknown leap second bitmap returned"
            yield Result(
                state=leap_state,
                summary=f"{leap_summary} (0b{leap_value:02b})",
            )
            if leap_metric is not None:
                yield Metric(name="leap_info", value=leap_metric)
        case _:
            raise ValueError(
                f"Encountered item {item} not present in section {section}"
            )


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
