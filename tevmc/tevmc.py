#!/usr/bin/env python3

from copy import deepcopy
import os
import sys
import logging
from types import SimpleNamespace

from typing import Optional
from pathlib import Path
from importlib import import_module
from distutils.dir_util import copy_tree

import docker
from docker.models.containers import Container
from docker.models.networks import Network

from flask import Flask
from docker.types import LogConfig, Mount
from tevmc.config.typing import CommonDict, ConfigDict
from tevmc.utils import service_alias_to_fullname

from tevmc.routes import add_routes
from tevmc.services import DockerService

from .config import *
from .logging import Formatter, get_tevmc_logger


class TEVMCException(BaseException):
    ...


class TEVMController:

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        log_level: str = 'tevmc_info',
        root_pwd: Optional[Path] = None,
        config: Optional[dict] = None
    ):
        self.pid = os.getpid()
        self.client = docker.from_env()

        self.services = SimpleNamespace()
        self.config: ConfigDict
        self.network: Optional[Network]

        if logger is None:
            self.logger = get_tevmc_logger(log_level)
        else:
            self.logger = logger

        if not root_pwd:
            self.root_pwd = Path()
        else:
            self.root_pwd = root_pwd

        self.load_config(config=config)

        self.root_pwd.mkdir(parents=True, exist_ok=True)
        self.root_pwd = self.root_pwd.resolve()

        self.docker_wd = self.root_pwd / 'docker'
        self.docker_wd.mkdir(exist_ok=True)

        self.templates_dir = Path(__file__).parent / 'templates'
        if not self.templates_dir.is_dir():
            raise TEVMCException('templates dir not found')

        copy_tree(
            str(self.templates_dir / 'docker'),
            str(self.docker_wd))

        self.api = Flask(f'tevmc-{self.chain_name}-admin-api')

    def write_config(self):
        write_config(
            self.config.model_dump(), str(self.root_pwd), 'tevmc.json')

    def update_configs(self):
        for service in vars(self.services).values():
            service.load_config()

    def load_config(
        self,
        config: Optional[Dict[str, Any]] = None,
        target: Optional[Path] = None
    ):
        if not target:
            target = self.root_pwd / 'tevmc.json'

        if not config:
            with open(target, 'r') as config_file:
                config: Dict[str, Any] = json.loads(config_file.read())

        else:
            config = deepcopy(config)

        self.config = ConfigDict(**config)

        # darwin arch doesn't support host networking mode...
        if self.config.daemon.network or sys.platform == 'darwin':
            self.network = self.network_setup(
                self.config.daemon.network
                if self.config.daemon.network
                else self.chain_name
            )
        else:
            self.network = None

        self.chain_name = self.config.rpc.elastic_prefix
        self.chain_type = 'local'
        if 'testnet' in self.chain_name:
            self.chain_type = 'testnet'
        elif 'mainnet' in self.chain_name:
            self.chain_type = 'mainnet'

        self.update_configs()

    def construct_service(self, service_alias: str) -> DockerService:
        service_name = service_alias_to_fullname(service_alias)
        module = import_module(f'tevmc.services.{service_name}')
        return module.Service(
            self,
            service_name,
            self.root_pwd
        )

    def build_service(self, service_name: str, **kwargs):
        if service_name not in self.config.model_dump():
            service_name = service_alias_to_fullname(service_name)

        service: DockerService = getattr(self.services, service_name)

        build_logs = ''
        accumulated_status = ''
        for chunk in self.client.api.build(
            tag=service.container_image,
            path=str(service.build_dir),
            **kwargs
        ):
            _str = chunk.decode('utf-8').rstrip()
            splt_str = _str.split('\n')

            for packet in splt_str:
                msg = json.loads(packet)
                status = msg.get('stream', '')

                if status:
                    accumulated_status += status
                    if '\n' in accumulated_status:
                        lines = accumulated_status.split('\n')
                        for line in lines[:-1]:
                            if service.config.show_build:
                                self.logger.tevmc_info(line)

                            build_logs += line
                        accumulated_status = lines[-1]

        try:
            self.client.images.get(service.container_image)

        except docker.errors.NotFound:
            self.logger.tevmc_error(build_logs.rstrip())
            raise TEVMCException(
                f'couldn\'t build container {service.container_image} at '
                f'{service.build_dir}')

    def launch_service_container(self, service: DockerService) -> Container:
        # check if there already is a container running from that image
        found = self.client.containers.list(
            filters={'name': service.container_name, 'status': 'running'})

        if len(found) > 0:
            raise TEVMCException(
                f'Container from image \'{service.container_name}\' is already running.')

        # check if image is present
        local_images = []
        for img in self.client.images.list(all=True):
            local_images += img.tags

        if service.container_image not in local_images:
            raise TEVMCException(f'Image \'{image}\' not found.')

        kwargs = deepcopy(service.more_params)
        if self.network:
            # set to bridge, and connect to our custom virtual net after Launch
            # this way we can set the ip addr
            kwargs['network'] = 'bridge'

        else:
            kwargs['network'] = 'host'

        extra_mounts = []
        if service.config.mounts:
            extra_mounts = [
                Mount(m.target, m.source, m.mtype) for m in service.config.mounts]

        # finally run container
        self.logger.tevmc_info(f'launching {service.container_name}...')
        container = self.client.containers.run(
            service.container_image,
            name=service.container_name,
            mounts=service.mounts + extra_mounts,
            environment=service.environment,
            detach=True,
            log_config=LogConfig(
                type=LogConfig.types.JSON,
                config={'max-size': '100m'}),
            labels=DEFAULT_DOCKER_LABEL,
            **kwargs
        )

        container.reload()
        self.logger.tevmc_info(f'immediate status: {container.status}')
        return container

    def stream_logs(self, source: str, **kwargs):
        for log in getattr(self.services, source).stream_logs(**kwargs):
            yield log

    def network_setup(self, name: str):
        self.logger.tevmc_info(f'setting up network {name}...')
        try:
            self.network = self.client.networks.get(name)

        except docker.errors.NotFound:
            ipam_pool = docker.types.IPAMPool(
                subnet='192.168.123.0/24',
                gateway='192.168.123.254'
            )
            ipam_config = docker.types.IPAMConfig(
                pool_configs=[ipam_pool]
            )

            self.network = self.client.networks.create(
                name, 'bridge', ipam=ipam_config
            )

        self.logger.tevmc_info(f'network online')

    def network_ip(self, service: str) -> str:
        service = service_alias_to_fullname(service)
        if hasattr(self.services, service):
            return getattr(self.services, service).ip

        if service in self.config.model_dump():
            config: CommonDict = getattr(self.config, service)
            return '127.0.0.1' if not config.virtual_ip else config.virtual_ip

        raise AttributeError('Couldn\'t figure out ip for {service}')

    def network_service_setup(self, service: DockerService):
        self.logger.tevmc_info(f'connecting {service.name} to network {self.network.name}...')
        self.network.connect(
            service.container,
            ipv4_address=service.config.virtual_ip
        )
        self.logger.tevmc_info(f'{service.name} connected.')

    def launch_service(self, service_name: str):
        name = service_alias_to_fullname(service_name)
        if hasattr(self.services, name):
            service = getattr(self.services, name)

        else:
            self.logger.tevmc_info(f'{name} not found, initializing...')
            service: DockerService = self.construct_service(name)

        self.logger.tevmc_info(f'prepare {name}')
        service.prepare()
        service.container = self.launch_service_container(service)

        if service.startup_phrase and service.config.wait_startup:
            phrase = service.startup_phrase

            self.logger.tevmc_info(
                f'waiting until phrase \"{phrase}\" is present in {name} logs.')

            found_phrase = False
            for msg in service.stream_logs(**service.startup_logs_kwargs):
                if service.config.show_startup:
                    self.logger.tevmc_info(msg.rstrip())

                if service.startup_phrase in msg:
                    found_phrase = True
                    self.logger.tevmc_info('found phrase!')
                    break

            if not found_phrase:
                raise TEVMCException(
                    f'timed out waiting for phrase \"{phrase}\" to be present '
                    f'in {name}\'s logs.')

        if self.network:
            self.network_service_setup(service)

        if not service.running:
            raise TEVMCException(
                f'service: {service.name} not running.')

        self.logger.tevmc_info(f'start {name}')
        service.start()
        self.logger.tevmc_info(f'started {name}')

    def initialize(self):
        for service_alias in self.config.daemon.services:
            service_name = service_alias_to_fullname(service_alias)
            setattr(self.services, service_name, self.construct_service(service_name))

    def start(self):
        self.logger.tevmc_info('tevmc starting...')
        try:
            for service in vars(self.services).values():
                service.load_templates()
                service.configure()
                self.build_service(service.name)

            for service in vars(self.services).values():
                self.launch_service(service.name)

            self.logger.tevmc_info('tevmc finished start')

        except BaseException:
            self.stop()
            raise

    def restart_service(self, service_name: str):
        service: DockerService = getattr(self.services, service_name)
        service.stop()
        service.load_templates()
        service.configure()
        self.build_service(service.name)
        self.launch_service(service_name)

    def serve_api(self):
        add_routes(self)
        self.api.run(port=self.config.daemon.port)

    def stop(self):
        self.logger.tevmc_info('tevmc is stopping...')
        for service in vars(self.services).values():
            service.stop()
            self.logger.tevmc_info(f'stopped {service.name}')

        if not self.config.daemon.testing:
            pid_path = self.root_pwd / 'tevmc.pid'
            if pid_path.is_file():
                pid_path.unlink(missing_ok=True)

        self.logger.tevmc_info('tevmc stopped')

    def __enter__(self):
        self.initialize()
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()
