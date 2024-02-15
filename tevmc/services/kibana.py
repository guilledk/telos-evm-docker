#!/usr/bin/env python3

import sys
import time
from typing import List, Optional

import requests
import simplejson

from tevmc.config.typing import KibanaDict

from . import DockerService, Mount


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: KibanaDict

        self.template_whitelist = [
            ('docker/kibana/build/Dockerfile', 'build/Dockerfile'),
            ('docker/kibana/config/kibana.yml', 'config/kibana.yml')
        ]

    @property
    def startup_phrase(self) -> Optional[str]:
        return 'Kibana is now available'

    def prepare(self):
        config_elastic = self.tevmc.config.elasticsearch

        self.mounts = [
            Mount('/usr/share/kibana/config', str(self.config_dir.resolve()), 'bind'),
            Mount('/data', str(self.data_dir.resolve()), 'bind')
        ]

        if self.tevmc.network:
            kibana_port = self.config.port
            self.more_params['ports'] = {f'{kibana_port}/tcp': kibana_port}

        elastic_ip = self.tevmc.network_ip('elastic')
        elastic_host = f'{config_elastic.protocol}://{elastic_ip}:{config_elastic.port}'

        self.environment = {
            'ELASTICSEARCH_HOSTS': elastic_host
        }

    def start(self):
        idx_version = self.tevmc.config.rpc.elasitc_index_version
        self.setup_index_patterns([
            f'{self.tevmc.chain_name}-action-{idx_version}-*',
            f'{self.tevmc.chain_name}-delta-{idx_version}-*',
            'filebeat-*'
        ])

    def setup_index_patterns(self, patterns: List[str]):
        kibana_port = self.config.port
        kibana_host = self.ip

        for pattern_title in patterns:
            self.logger.info(
                f'registering index pattern \'{pattern_title}\'')
            while True:
                try:
                    resp = requests.post(
                        f'http://{kibana_host}:{kibana_port}'
                        '/api/index_patterns/index_pattern',
                        headers={'kbn-xsrf': 'true'},
                        json={
                            "index_pattern" : {
                                "title": pattern_title,
                                "timeFieldName": "@timestamp"
                            }
                        }).json()
                    self.logger.debug(resp)

                except requests.exceptions.ConnectionError:
                    self.logger.warning('can\'t reach kibana, retry in 3 sec...')

                except simplejson.errors.JSONDecodeError:
                    self.logger.info('kibana server not ready, retry in 3 sec...')

                else:
                    break

                time.sleep(3)
            self.logger.info('registered.')
