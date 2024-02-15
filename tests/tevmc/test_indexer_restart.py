#!/usr/bin/env python3

import pytest

from tevmc.testing.database import ElasticDriver


@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_indexer_restart_simple(tevmc_local):
    tevmc = tevmc_local

    tevmc.restart_service('translator')

    elastic = ElasticDriver(tevmc.config.model_dump())
    elastic.full_integrity_check()
