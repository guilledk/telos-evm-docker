#!/usr/bin/env python3

import re
import time
from typing import Optional

import requests

from tevmc.config.typing import TranslatorDict

from . import DockerService


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: TranslatorDict

        self.startup_logs_kwargs = { 'timeout': 60*10 }

        self.template_whitelist = [
            ('docker/translator/build/Dockerfile', 'build/Dockerfile')
        ]

    @property
    def startup_phrase(self) -> Optional[str]:
        return 'drained'

    def configure(self):
        self.config_subst.update({
            'broadcast_port': self.tevmc.config.rpc.indexer_websocket_port
        })

        super().configure()

    def prepare(self):
        config_elastic = self.tevmc.config.elasticsearch
        config_nodeos = self.tevmc.config.nodeos
        config_rpc = self.tevmc.config.rpc

        nodeos_host = self.tevmc.network_ip('nodeos')

        nodeos_api_port = config_nodeos.ini.http_addr.split(':')[1]
        nodeos_ship_port = config_nodeos.ini.history_endpoint.split(':')[1]
        endpoint = f'http://{nodeos_host}:{nodeos_api_port}'

        if self.tevmc.chain_type == 'testnet':
            remote_endpoint = 'https://testnet.telos.net'
        elif self.tevmc.chain_type == 'mainnet':
            remote_endpoint = 'https://mainnet.telos.net'
        else:
            remote_endpoint = endpoint

        ws_endpoint = f'ws://{nodeos_host}:{nodeos_ship_port}'

        bc_host = config_rpc.indexer_websocket_host
        bc_port = config_rpc.indexer_websocket_port

        if self.tevmc.network:
            self.more_params['ports'] = {f'{bc_port}/tcp': bc_port}

        elastic_ip = self.tevmc.network_ip('elastic')
        elastic_host = f'{config_elastic.protocol}://{elastic_ip}:{config_elastic.port}'

        self.environment = {
            'CHAIN_NAME': self.tevmc.chain_name,
            'CHAIN_ID': str(config_rpc.chain_id),
            'ELASTIC_NODE': elastic_host,
            'ELASTIC_DUMP_SIZE': str(self.config.elastic_dump_size),
            'ELASTIC_TIMEOUT': str(self.config.elastic_timeout),
            'TELOS_ENDPOINT': endpoint,
            'TELOS_REMOTE_ENDPOINT': remote_endpoint,
            'TELOS_WS_ENDPOINT': ws_endpoint,
            'INDEXER_START_BLOCK': str(self.config.start_block),
            'INDEXER_STOP_BLOCK': str(self.config.stop_block),
            'EVM_DEPLOY_BLOCK': str(self.config.deploy_block),
            'EVM_PREV_HASH': self.config.prev_hash,
            'EVM_START_BLOCK': str(self.config.evm_start_block),
            'EVM_VALIDATE_HASH': self.config.evm_validate_hash,
            'BROADCAST_HOST': bc_host,
            'BROADCAST_PORT': str(bc_port),
            'WORKER_AMOUNT': str(self.config.worker_amount)
        }

    def start(self):
        if (self.tevmc.chain_type != 'local' and
            self.tevmc.config.daemon.wait_sync):
            self.await_full_index()

    def await_full_index(self):
        last_indexed_block = 0
        remote_head_block = self.tevmc.services.nodeos._get_remote_head_block()
        last_update_time = time.time()
        delta = remote_head_block - self.tevmc.cleos.get_info()['head_block_num']

        for line in self.stream_logs():
            if '] pushed, at ' in line:
                m = re.findall(r'(?<=: \[)(.*?)(?=\|)', line)
                if len(m) == 1 and m[0] != 'NaN':
                    last_indexed_block = int(m[0].replace(',', ''))

                    delta = remote_head_block - last_indexed_block

            self.logger.info(
                f'waiting on sync... delta: {"{:,}".format(delta)}')

            if delta < 100:
                break

            now = time.time()
            if now - last_update_time > 3600:
                remote_head_block = self.tevmc.services.nodeos._get_remote_head_block()
                last_update_time = now
