#!/usr/bin/env python3

import sys
import json

from string import Template
from typing import Dict
from pathlib import Path
from datetime import datetime
from distutils.dir_util import copy_tree

import click

from .cli import cli
from ..config import local, testnet, mainnet


source_dir = Path(__file__).parent
template_dir = (source_dir / '../templates').resolve(strict=False)


def load_config_templates() -> Dict[str, Template]:
    templ = {}
    for node in (template_dir / 'config').glob('*'):
        if node.is_file():
            with open(node, 'r') as templ_file:
                templ[node.name] = Template(templ_file.read())
    return templ


def load_docker_templates() -> Dict[str, Template]:
    templ = {}
    for node in (template_dir / 'docker').glob('**/*'):
        if node.is_file():
            with open(node, 'r') as templ_file:
                try:
                    key = '/'.join(node.parts[-3:])
                    templ[key] = Template(templ_file.read())
                except UnicodeDecodeError:
                    pass

    return templ


def touch_node_dir(target_dir, conf, fname):
    # dump default config file
    with open(target_dir / fname, 'w+') as uni_conf:
        uni_conf.write(json.dumps(conf, indent=4))

    # copy new directory tree template
    copy_tree(
        str(template_dir / 'docker'),
        str(target_dir / 'docker'))


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.argument('chain-name')
def init(config, target_dir, chain_name):

    if not template_dir.is_dir():
        print('Template directory not found.')
        sys.exit(1)

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
   
    target_dir = target_dir / chain_name
    target_dir.mkdir(parents=True, exist_ok=True)

    touch_node_dir(target_dir, conf, config)

