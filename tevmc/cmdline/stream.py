#!/usr/bin/env python3

import subprocess

from pathlib import Path

import click

from tevmc.utils import service_alias_to_fullname

from .cli import cli
from ..config import load_config


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--logpath', default='tevmc.log',
    help='Log file path.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.argument('source')
def stream(pid, logpath, target_dir, config, source):
    """Stream logs from either the tevmc daemon or a container.
    """
    config = load_config(target_dir, config)

    try:
        with open(pid, 'r') as pidfile:
            pid = int(pidfile.read())

    except FileNotFoundError:
        print('daemon not running.')

    source = service_alias_to_fullname(source)

    try:
        if source == 'daemon':
            subprocess.run(['tail', '-f', logpath])
            return

        chain_name = config['rpc']['elastic_prefix']
        src_config = config[source]

        if source == 'nodeos':
            nos_docker = src_config['docker_path']
            nos_config = src_config['config_path']
            filename = src_config['logs_file']
            nodeos_log_file = target_dir
            nodeos_log_file += f'/docker/{nos_docker}/{nos_config}/{filename}'
            subprocess.run(
                ['tail', '-f', nodeos_log_file])

        elif source in config:
            container_name = f'{chain_name}-{pid}-{src_config["name"]}'
            subprocess.run(
                ['docker', 'logs', '-f', container_name])

        else:
            print(f'Can\'t stream from source \"{source}\"')

    except KeyboardInterrupt:
        print('Interrupted.')
