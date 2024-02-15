#!/usr/bin/env python3

import logging
import docker

import pytest

from tevmc.cmdline.repair import perform_data_repair
from tevmc.config import load_config, write_config


EVM_1_5_ENDPOINT = 'https://mainnet15a.telos.net/evm'


@pytest.mark.randomize(False)
@pytest.mark.services('redis', 'elastic', 'nodeos', 'indexer')
def test_repair_dirty_db(tevmc_mainnet):
    tevmc = tevmc_mainnet

    tevmc.cleos.wait_blocks(110_000)

    nodeos_service = tevmc.services.nodeos

    # ungracefull nodeos stop
    try:
        for i in range(3):
            nodeos_service.container.reload()
            nodeos_service.container.stop()

    except docker.errors.APIError:
        ...

    # tear down node
    tevmc.stop()

    # assert db is dirty
    tevmc.load_config()
    tevmc.config.nodeos.api_check = False
    tevmc.config.nodeos.wait_startup = False
    tevmc.update_configs()
    tevmc.restart_service('nodeos')
    is_dirty = False
    for line in nodeos_service.stream_logs(lines=10):
        logging.info(line.rstrip())
        if 'database dirty flag set (likely due to unclean shutdown)' in line:
            is_dirty = True
            break

    assert is_dirty

    tevmc.stop()

    # run repair
    perform_data_repair(
        tevmc.root_pwd / 'tevmc.json', progress=False)

    # add rpc service & update config
    tevmc.load_config()
    tevmc.config.daemon.services += ['rpc']
    tevmc.update_configs()

    # pull up node
    tevmc.initialize()
    tevmc.start()
    tevmc.cleos.wait_blocks(10_000)

    # get latest evm block
    block = tevmc.cleos.eth_get_block_by_number('latest')['result']

    # query remote for same block
    remote_block = tevmc.cleos.eth_get_block_by_number(
        block['number'], url=EVM_1_5_ENDPOINT)['result']

    # check hashes match
    assert block['hash'] == remote_block['hash']
