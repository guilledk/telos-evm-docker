#!/usr/bin/env python3

from tevmc.testing.database import ElasticDriver


def test_restart(tevmc_mainnet):
    tevmc = tevmc_mainnet

    tevmc.stop()

    assert (
        tevmc.services.nodeos.data_dir / 'blocks/blocks.log').is_file()

    tevmc.start()

    ElasticDriver(
        tevmc_mainnet.config.model_dump()).full_integrity_check()
