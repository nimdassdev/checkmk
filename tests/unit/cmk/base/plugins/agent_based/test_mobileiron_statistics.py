#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.mobileiron_section import parse_mobileiron_statistics
from cmk.base.plugins.agent_based.mobileiron_statistics import check_mobileiron_sourcehost
from cmk.base.plugins.agent_based.utils.mobileiron import SourceHostSection

DEVICE_DATA = parse_mobileiron_statistics([['{"non_compliant": 12, "total_count": 22}']])


@pytest.mark.parametrize(
    "params, section, expected_results",
    [
        (
            {"non_compliant_summary_levels": (10, 20)},
            DEVICE_DATA,
            (
                Metric("mobileiron_devices_total", 22),
                Metric("mobileiron_non_compliant", 12.0),
                Result(
                    state=State.CRIT,
                    summary="Number of non-compliant devices: 12 out of 22: 54.55% (warn/crit at 10.00%/20.00%)",
                ),
            ),
        ),
        (
            {"non_compliant_summary_levels": (50, 60)},
            DEVICE_DATA,
            (
                Metric("mobileiron_devices_total", 22),
                Metric("mobileiron_non_compliant", 12.0),
                Result(
                    state=State.WARN,
                    summary="Number of non-compliant devices: 12 out of 22: 54.55% (warn/crit at 50.00%/60.00%)",
                ),
            ),
        ),
    ],
)
def test_check_mobileiron_sourcehost(
    params: Mapping[str, Any], section: SourceHostSection, expected_results: CheckResult
) -> None:
    results = tuple(check_mobileiron_sourcehost(params, section))
    assert results == expected_results
