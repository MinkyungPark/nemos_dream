"""Pytest root config — exposes canned sample rows as fixtures."""

from __future__ import annotations

import pytest

from tests.fixtures.sample_rows import sample_raw, sample_stage1, sample_stage2, sample_stage3


@pytest.fixture
def raw_row():
    return sample_raw()


@pytest.fixture
def stage1_row():
    return sample_stage1()


@pytest.fixture
def stage2_row():
    return sample_stage2()


@pytest.fixture
def stage3_row():
    return sample_stage3()
