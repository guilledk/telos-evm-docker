#!/usr/bin/env python3

from abc import ABC
from string import Template
from typing import Any, List, Optional
from pathlib import Path
from datetime import datetime

import docker

from leap.sugar import docker_open_process, docker_wait_process
from docker.types import Mount
from docker.models.containers import Container

from tevmc.utils import docker_stream_logs, flatten
from tevmc.config import write_templated_file


class DockerService(ABC):

    def __init__(
        self,
        tevmc,
        name: str,
        root_pwd: Path
    ):
        self.tevmc = tevmc
        self.name = name
        self.load_config()
        self.root_pwd = root_pwd
        self.logger = tevmc.logger

        self.template_whitelist: list[tuple[str, str]] = []
        self.templates: dict[str, Template] = {}

        self.mounts: List[Mount] = []
        self.more_params: dict[str, Any] = {}
        self.environment: dict[str, str] = {}

        self.container: Optional[Container] = None

        self.startup_logs_kwargs: dict[str, Any] = {}

        self.docker_wd = root_pwd / 'docker'
        self.service_dir = self.docker_wd / self.config.docker_path
        self.build_dir = self.service_dir / self.config.build_path

        # optional dirs
        self.config_dir = (
            self.service_dir / self.config.config_path
            if self.config.config_path else None
        )
        self.data_dir = (
            self.service_dir / self.config.data_path
            if self.config.data_path else None
        )
        self.logs_dir = (
            self.service_dir / self.config.logs_path
            if self.config.logs_path else None
        )

        if self.build_dir:
            self.build_dir.mkdir(exist_ok=True, parents=True)

        if self.config_dir:
            self.config_dir.mkdir(exist_ok=True, parents=True)

        if self.data_dir:
            self.data_dir.mkdir(exist_ok=True, parents=True)

        if self.logs_dir:
            self.logs_dir.mkdir(exist_ok=True, parents=True)

        self.config_subst = flatten(self.name, self.tevmc.config.model_dump())

    @property
    def startup_phrase(self) -> Optional[str]:
        return None

    def load_config(self):
        self.config = getattr(self.tevmc.config, self.name)
        self.container_name = f'{self.tevmc.chain_name}-{self.tevmc.pid}-{self.config.name}'
        self.container_image = f'{self.config.tag}-{self.tevmc.chain_name}'

    def load_templates(self):
        for tsrc, tdst in self.template_whitelist:
            with open(self.tevmc.templates_dir / tsrc, 'r') as templ_file:
                self.templates[tdst] = Template(templ_file.read())
        self.logger.tevmc_info(f'loaded {len(self.template_whitelist)} {self.name} templates')

    def configure(self):
        self.ip = '127.0.0.1' if not self.config.virtual_ip else self.config.virtual_ip
        self.config_subst['timestamp'] = str(datetime.now())
        for templ_path, template in self.templates.items():
            target = self.service_dir / templ_path
            self.logger.info(f'generating {target}...')
            write_templated_file(target, template, self.config_subst)
            self.logger.info('done')

    def prepare(self):
        ...

    def start(self):
        ...

    def stream_logs(self, **kwargs):
        if not self.container:
            return

        for chunk in docker_stream_logs(self.container, **kwargs):
            yield chunk

    def open_process(self, *args, **kwargs):
        return docker_open_process(
            self.tevmc.client,
            self.container,
            *args, **kwargs
        )

    def run_process(self, *args, **kwargs):
        return docker_wait_process(
            self.tevmc.client,
            *(self.open_process(*args, **kwargs)))

    def stop(self):
        if not self.container:
            return

        try:
            self.container.reload()

            if self.container.status == 'running':
                try:
                    for _ in range(3):
                        self.container.stop()

                except docker.errors.APIError:
                    ...

            self.container.remove()

        except docker.errors.NotFound:
            ...

    @property
    def running(self) -> bool:
        if self.container:
            try:
                self.container.reload()
                return self.container.status == 'running'

            except docker.errors.NotFound:
                ...

        return False

