#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        ({}, ["-H", "$HOSTADDRESS$"]),
        ({"port": 21}, ["-H", "$HOSTADDRESS$", "-p", 21]),
    ],
)
def test_check_ftp_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[object]
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_ftp")
    assert active_check.run_argument_function(params) == expected_args
