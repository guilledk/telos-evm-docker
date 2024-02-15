#!/usr/bin/env python3

import time

from . import DockerService, Mount


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.template_whitelist = [
            ('docker/beats/build/Dockerfile', 'build/Dockerfile')
        ]

    def prepare(self):
        config_elastic = self.tevmc.config.elasticsearch
        config_kibana = self.tevmc.config.kibana
        config_rpc = self.tevmc.config.rpc

        rpc_docker_dir = self.docker_wd / config_rpc.docker_path
        data_dir = rpc_docker_dir / config_rpc.logs_path

        data_dir.mkdir(parents=True, exist_ok=True)

        self.mounts = [
            Mount('/etc/filebeat', str(self.config_dir.resolve()), 'bind'),
            Mount('/root/logs', str(data_dir.resolve()), 'bind')
        ]

        elastic_ip = self.tevmc.network_ip('elastic')
        elastic_host = f'{config_elastic.protocol}://{elastic_ip}:{config_elastic.port}'

        self.environment={
            'CHAIN_NAME': self.tevmc.chain_name,
            'ELASTIC_HOST': elastic_host,
            'KIBANA_HOST': f'localhost:{config_kibana.port}'
        }

    def start(self):
        ec, out = self.run_process(['chown', '-R', '0:0', '/etc/filebeat/filebeat.yml'])
        assert ec == 0

        ec, out = self.run_process(['chmod', '600', '/etc/filebeat/filebeat.yml'])
        assert ec == 0

        self.beat_id, self.beat_stream = self.open_process(['filebeat', '-e'])

        time.sleep(3)

        ec, out = self.run_process(['filebeat', 'setup', '--pipelines'])
        if ec != 0:
            self.logger.error('filebeats pipeline setup error: ')
            self.logger.error(out)

        else:
            self.logger.info('pipelines setup')

