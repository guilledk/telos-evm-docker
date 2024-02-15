#!/usr/bin/env python3

from typing import Optional
from tevmc.config.typing import ElasticsearchDict

from . import DockerService, Mount


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: ElasticsearchDict

        self.template_whitelist = [
            ('docker/elasticsearch/build/Dockerfile', 'build/Dockerfile'),
            ('docker/elasticsearch/build/elasticsearch.yml', 'build/elasticsearch.yml')
        ]

    @property
    def startup_phrase(self) -> Optional[str]:
        return ' indices into cluster_state'

    def prepare(self):
        self.mounts = [
            Mount('/home/elasticsearch/logs', str(self.logs_dir.resolve()), 'bind'),
            Mount('/home/elasticsearch/data', str(self.data_dir.resolve()), 'bind')
        ]

        self.more_params['user'] = 'root'

        if self.tevmc.network:
            es_port = int(self.config.port)
            self.more_params['ports'] = {f'{es_port}/tcp': es_port}

        self.environment = {
            'discovery.type': 'single-node',
            'cluster.name': 'es-cluster',
            'node.name': 'es01',
            'bootstrap.memory_lock': 'true',
            'xpack.security.enabled': 'false',
            'ES_JAVA_OPTS': '-Xms2g -Xmx2g',
            'ES_NETWORK_HOST': '0.0.0.0'
        }
