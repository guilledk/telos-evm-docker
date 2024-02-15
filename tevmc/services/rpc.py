#!/usr/bin/env python3

import time
from typing import Optional

from docker.types import Mount
from websocket import create_connection
from tevmc.config.typing import RpcDict

from tevmc.utils import flatten, jsonize

from . import DockerService


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: RpcDict

        self.template_whitelist = [
            ('docker/rpc/build/Dockerfile', 'build/Dockerfile'),
            ('docker/rpc/build/config.json', 'build/config.json')
        ]

    @property
    def startup_phrase(self) -> Optional[str]:
        return 'Telos EVM RPC started!!!'

    def configure(self):
        self.config_subst = self.config_subst

        config_elastic = self.tevmc.config.elasticsearch
        config_nodeos = self.tevmc.config.nodeos
        config_redis = self.tevmc.config.redis
        nodeos_api_port = int(config_nodeos.ini.http_addr.split(':')[1])
        elastic_ip = self.tevmc.network_ip('elastic')
        elastic_host = f'{config_elastic.protocol}://{elastic_ip}:{config_elastic.port}'

        self.config_subst.update(jsonize(flatten('rpc', self.tevmc.config.model_dump())))

        self.config_subst.update(jsonize({
            'redis_host': config_redis.host,
            'redis_port': config_redis.port,
            'rpc_nodeos_read': f'http://{elastic_ip}:{nodeos_api_port}',
            'rpc_elastic_node': elastic_host,
            'elasticsearch_user': '',
            'elasticsearch_pass': '',
            'elasticsearch_prefix': self.config.elastic_prefix,
            'elasticsearch_index_version': self.config.elasitc_index_version
        }))

        super().configure()

    def prepare(self):
        self.mounts = [
            Mount('/root/.pm2/logs', str(self.logs_dir.resolve()), 'bind')
        ]

        if self.tevmc.network:
            api_port = self.config.api_port
            rpc_port = self.config.websocket_port
            self.more_params['ports'] = {
                f'{api_port}/tcp': api_port,
                f'{rpc_port}/tcp': rpc_port
            }

    def open_rpc_websocket(self):
        rpc_ws_port = self.config.websocket_port

        rpc_endpoint = f'ws://{self.ip}:{rpc_ws_port}/evm'
        self.logger.info(f'connecting to {rpc_endpoint}')

        connected = False
        for i in range(3):
            try:
                ws = create_connection(rpc_endpoint)
                connected = True
                break

            except ConnectionRefusedError:
                time.sleep(5)

        assert connected
        return ws
