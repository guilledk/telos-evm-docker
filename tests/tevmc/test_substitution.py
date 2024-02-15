#!/usr/bin/env python3

import pytest

from leap.sugar import Asset

from web3 import Account


@pytest.mark.randomize(False)
@pytest.mark.services('nodeos')
def test_setcode_with_same_hash_subst(tevmc_local):
    tevmc = tevmc_local

    regular_path = '/opt/eosio/bin/contracts/eosio.evm/regular'
    receiptless_path = '/opt/eosio/bin/contracts/eosio.evm/receiptless'

    tevmc.cleos.deploy_contract(
        'eosio.evm', regular_path,
        privileged=True,
        create_account=False,
        verify_hash=False)

    tevmc.cleos.deploy_contract(
        'eosio.evm', receiptless_path,
        privileged=True,
        create_account=False,
        verify_hash=False)

    tevmc.cleos.wait_blocks(10)

    eth_addr = tevmc.cleos.eth_account_from_name('evmuser1')
    assert eth_addr
    ec, _ = tevmc.cleos.eth_transfer(
        'evmuser1',
        eth_addr,
        Account.create().address,
        Asset(1, tevmc.cleos.sys_token_supply.symbol)
    )
    assert ec == 0

    found_receipt = False
    for log in tevmc.stream_logs('nodeos', lines=5, timeout=4):
        if 'RCPT' in log:
            found_receipt = True

    assert found_receipt

