#!/usr/bin/env python3

import time
import requests

from typing import Optional

from py_eosio.cleos import CLEOS


class ETHRPCError(BaseException):
    ...


class CLEOSEVM(CLEOS):

    def __init__(
        self,
        *args, 
        hyperion_api_endpoint: str = 'http://127.0.0.1:7000',
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self.hyperion_api_endpoint = hyperion_api_endpoint

        self.__jsonrpc_id = 0


    """    eosio.evm interaction
    """

    def get_evm_config(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'config')

    def get_evm_resources(self):
        return self.get_table(
            'eosio.evm', 'eosio.evm', 'resources')

    def eth_account_from_name(self, name) -> Optional[str]:
        rows = self.get_table(
            'eosio.evm', 'eosio.evm', 'account',
            '--key-type', 'name', '--index', '3',
            '--lower', name,
            '--upper', name)
        
        if len(rows) != 1:
            return None

        return f'0x{rows[0]["address"]}'

    def create_evm_account(
        self,
        account: str,
        salt: str
    ):
        return self.push_action(
            'eosio.evm',
            'create',
            [account, salt],
            f'{account}@active'
        )

    """    hyperion interaction
    """
    def hyperion_health(self) -> int:
        return requests.get(
            f'{self.hyperion_api_endpoint}/v2/health').json()

    # def hyperion_await_evm_tx(self, tx_hash):
    #     while True:
    #         resp = requests.get(
    #             f'{self.hyperion_api_endpoint}/v2/evm/get_transactions',
    #             params={'hash': tx_hash}).json()

    #         breakpoint()

    def hyperion_await_tx(self, tx_id):
        while True:
            resp = requests.get(
                f'{self.hyperion_api_endpoint}/v2/history/get_transaction',
                params={'id': tx_id}).json()

            if 'executed' not in resp:
                self.logger.warning(resp)

            if resp['executed']:
                break

            self.logger.info('await transaction:')
            self.logger.info(resp)
            time.sleep(0.1)

    def hyperion_get_actions(self, **kwargs):
        return requests.get(
            f'{self.hyperion_api_endpoint}/v2/history/get_actions',
            params=kwargs
        ).json()

    """ EVM RPC
    """

    def evm_rpc(self, method, params):
        ret = requests.post(
            f'{self.hyperion_api_endpoint}/evm',
            json={
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': self.__jsonrpc_id
            }).json()

        self.__jsonrpc_id += 1
        return ret

    def eth_block_num(self):
        return self.evm_rpc(
            'eth_blockNumber', [])

    def eth_get_balance(self, address: int):
        resp = self.evm_rpc(
            'eth_getBalance', [address])

        if 'error' in resp:
            raise ETHRPCError(resp['error'])

        return int(resp['result'], 16)


    # def wait_eth_blocks(self, num: int):
    #     start_block = self.eth_block_num()
    #     breakpoint()
