#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [
    ["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["san_vc0_0001dc", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["md36xxf0_4", "ENABLED", "MD36xxf", "4", "4", "0", "md36xxf0"],
]

STRING_TABLE_WITH_ERROR = [
    ["===================================="],
    ["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["san_vc0_0001dc", "ENABLED", "SAN_VC", "8", "8", "0", "san_vc0"],
    ["md36xxf0_4", "ENABLED", "MD36xxf", "4", "4", "0", "md36xxf0"],
]


@pytest.fixture(name="check")
def _vxvm_multipath_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("vxvm_multipath")]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="san_vc0_0001da"),
                Service(item="san_vc0_0001dc"),
                Service(item="md36xxf0_4"),
            ],
            id="Discovery with section that has no error.",
        ),
        pytest.param(
            STRING_TABLE_WITH_ERROR,
            [
                Service(item="===================================="),
                Service(item="san_vc0_0001da"),
                Service(item="san_vc0_0001dc"),
                Service(item="md36xxf0_4"),
            ],
            id="Discovery with section that has an error.",
        ),
    ],
)
def test_discover_vxvm_multipath(
    check: CheckPlugin,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(check.discovery_function(section)) == expected_discovery_result


@pytest.mark.parametrize(
    "item, section, expected_check_result",
    [
        pytest.param(
            "san_vc0_0001da",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: ENABLED, (8/8) Paths to enclosure san_vc0 enabled",
                )
            ],
            id="The number of active paths is the same as the number of maximum available paths. Because of that, the state is OK.",
        ),
        pytest.param(
            "san_vc0_0001da",
            [["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "5", "0", "san_vc0"]],
            [
                Result(
                    state=State.WARN,
                    summary="Status: ENABLED, (5/8) Paths to enclosure san_vc0 enabled",
                )
            ],
            id="The number of active paths is not the same as the number of maximum available paths, so the state is WARN.",
        ),
        pytest.param(
            "san_vc0_0001da",
            [["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "5", "3", "san_vc0"]],
            [
                Result(
                    state=State.WARN,
                    summary="Status: ENABLED, (5/8) Paths to enclosure san_vc0 enabled",
                )
            ],
            id="The number of inactive paths is greater than 0, so the state is CRIT.",
        ),
        pytest.param(
            "not_found",
            [["san_vc0_0001da", "ENABLED", "SAN_VC", "8", "5", "3", "san_vc0"]],
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Item not found",
                )
            ],
            id="The item was not found, so the state is UNKNOWN.",
        ),
    ],
)
def test_check_vxvm_multipath(
    check: CheckPlugin,
    item: str,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check.check_function(
                item=item,
                params={},
                section=section,
            )
        )
        == expected_check_result
    )


def test_check_vxvm_multipath_with_error_section(
    check: CheckPlugin,
) -> None:
    with pytest.raises(ValueError):
        assert list(
            check.check_function(
                item="random_item",
                params={},
                section=[["===================================="]],
            )
        )
