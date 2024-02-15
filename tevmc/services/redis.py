#!/usr/bin/env python3

import sys
from typing import Optional

from tevmc.config.typing import RedisDict

from . import DockerService, Mount


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: RedisDict

        self.template_whitelist = [
            ('docker/redis/build/Dockerfile', 'build/Dockerfile'),
            ('docker/redis/config/redis.conf', 'config/redis.conf')
        ]

    @property
    def startup_phrase(self) -> Optional[str]:
        return 'Ready to accept connections'

    def prepare(self):
        self.mounts = [
            Mount('/root', str(self.config_dir.resolve()), 'bind'),
            Mount('/data', str(self.data_dir.resolve()), 'bind')
        ]

        if self.tevmc.network:
            self.more_params['ports'] = {
                f'{self.config.port}/tcp': self.config.port}

