#!/usr/bin/env python3

from copy import deepcopy

import pytest

from tevmc.config import testnet
from tevmc.testing.database import ElasticDriver


conf = deepcopy(testnet.default_config)
conf['translator']['worker_amount'] = 100
conf['translator']['elastic_dump_size'] = 1024

@pytest.mark.config(**conf)
@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_indexer_restart_multi_during_sync(tevmc_testnet):
    tevmc = tevmc_testnet

    for _ in range(20):
        tevmc.cleos.wait_blocks(10 * 1000)
        tevmc.services['translator'].restart()

        elastic = ElasticDriver(tevmc.config)
        elastic.full_integrity_check()
