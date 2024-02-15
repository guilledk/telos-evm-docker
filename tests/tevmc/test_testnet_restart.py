#!/usr/bin/env python3

from tevmc.testing.database import ElasticDriver


def test_restart(tevmc_testnet):
    tevmc = tevmc_testnet

    tevmc.stop()

    assert (
        tevmc.services['nodeos'].data_dir / 'blocks/blocks.log').is_file()

    tevmc.start()

    ElasticDriver(tevmc_testnet.config).full_integrity_check()
