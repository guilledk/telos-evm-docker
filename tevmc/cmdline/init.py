#!/usr/bin/env python3

import sys
import json

from pathlib import Path

import click

from .cli import cli
from ..config import (
    local, testnet, mainnet,
    randomize_conf_ports,
    add_virtual_networking
)


def touch_conf(target, conf):
    # dump default config file
    with open(target, 'w+') as uni_conf:
        uni_conf.write(json.dumps(conf, indent=4))


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--random-ports/--default-ports', default=False,
    help='Randomize port and node name, useful to boot '
         'multiple nodes on same host.')
@click.argument('chain-name')
def init(config, target_dir, chain_name, random_ports):

    target_dir = (Path(target_dir)).resolve(strict=False)

    if not target_dir.is_dir():
        print('Target directory not found.')
        sys.exit(1)

    conf = {}
    if 'local' in chain_name:
        conf = local.default_config

    elif 'testnet' in chain_name:
        conf = testnet.default_config

    elif 'mainnet' in chain_name:
        conf = mainnet.default_config

    if random_ports:
        conf = randomize_conf_ports(conf)

    if sys.platform == 'darwin':
        conf = add_virtual_networking(conf)

    target_dir = target_dir / chain_name
    target_dir.mkdir(parents=True, exist_ok=True)

    touch_conf(target_dir / config, conf)

