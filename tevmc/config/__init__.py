#!/usr/bin/env python3

import json
import socket
import random
from string import Template

from typing import Dict, List, Any
from pathlib import Path

import docker

from .default import local, testnet, mainnet


DEFAULT_DOCKER_LABEL = {'created-by': 'tevmc'}
DEFAULT_FILTER = {'label': DEFAULT_DOCKER_LABEL}

MAX_STATUS_SIZE = 54


def write_templated_file(
    target_dir: Path,
    template: Template,
    subst: Dict[str, Any]
):
    with open(target_dir, 'w+') as target_file:
        target_file.write(template.substitute(**subst))


def get_config(key, _dict):
    if key in _dict:
        return _dict[key]

    else:
        if '.' in key:
            splt_key = key.split('.')
            return get_config(
                '.'.join(splt_key[1:]),
                _dict[splt_key[0]])

        else:
            raise KeyError(f'{key} not in {_dict.keys()}')


def load_config(location: str, name: str) -> Dict[str, Dict]:
    target_dir = (Path(location)).resolve()
    config_file = (target_dir / name).resolve()

    with open(config_file, 'r') as config_file:
        return json.loads(config_file.read())

def write_config(config: dict, location: str, name: str):
    target_dir = (Path(location)).resolve()
    config_file = (target_dir / name).resolve()

    with open(config_file, 'w+') as config_file:
        config_file.write(json.dumps(config, indent=4))



def build_docker_manifest(config: Dict) -> List[str]:
    chain_name = config['telos-evm-rpc']['elastic_prefix']
    manifest = []
    for container_name, conf in config.items():
        if 'docker_path' not in conf:
            continue

        try:
            repo, tag = conf['tag'].split(':')
            tag = f'{tag}-{chain_name}'

        except ValueError:
            raise ValueError(
                f'Malformed tag {key}=\'{arg}\','
                f' must be of format \'{repo}:{tag}\'.')

        manifest.append((repo, tag))

    return manifest


def check_docker_manifest(client, manifest: List):
    for repo, tag in manifest:
        try:
            client.images.get(f'{repo}:{tag}')

        except docker.errors.NotFound:
            raise docker.errors.NotFound(
                f'Docker image \'{repo}:{tag}\' is required, please run '
                '\'tevmc build\' to build the required images.'
            )


def randomize_conf_ports(config: Dict) -> Dict:
    ret = config.copy()

    def get_free_port(tries=10):
        _min = 10000
        _max = 60000
        found = False

        for i in range(tries):
            port_num = random.randint(_min, _max)

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                s.bind(("127.0.0.1", port_num))
                s.close()

            except socket.error as e:
                continue

            else:
                return port_num

    # redis
    ret['redis']['port'] = get_free_port()

    # elasticsearch
    ret['elasticsearch']['port'] = get_free_port()

    # kibana
    ret['kibana']['port'] = get_free_port()

    # nodeos
    nodeos_http_port = get_free_port()
    state_history_port = get_free_port()
    ret['nodeos']['ini']['http_addr'] = f'0.0.0.0:{nodeos_http_port}'
    ret['nodeos']['ini']['p2p_addr'] = f'0.0.0.0:{get_free_port()}'
    ret['nodeos']['ini']['history_endpoint'] = f'0.0.0.0:{state_history_port}'

    # telos-evm-rpc
    idx_ws_port = get_free_port()
    ret['rpc']['indexer_websocket_port'] = idx_ws_port
    ret['rpc']['indexer_websocket_uri'] = f'ws://127.0.0.1:{idx_ws_port}/evm'

    ret['rpc']['websocket_port'] = get_free_port()

    ret['rpc']['api_port'] = get_free_port()

    if '127.0.0.1' in ret['rpc']['remote_endpoint']:
        ret['rpc']['remote_endpoint'] = f'http://127.0.0.1:{nodeos_http_port}/evm'

    return ret


def add_virtual_networking(config: Dict) -> Dict:
    ret = config.copy()

    ips = [
        f'192.168.123.{i}'
        for i in range(2, 9)
    ]

    # redis
    ret['redis']['virtual_ip'] = ips[0]

    # elastic
    ret['elasticsearch']['virtual_ip'] = ips[1]

    # kibana
    ret['kibana']['virtual_ip'] = ips[2]

    # nodeos
    ret['nodeos']['virtual_ip'] = ips[3]

    # beats
    ret['beats']['virtual_ip'] = ips[4]

    # translator
    ret['translator']['virtual_ip'] = ips[5]

    # rpc
    ret['rpc']['virtual_ip'] = ips[6]
    ret['rpc']['api_host'] = ips[6]
    indexer_ws_port = ret['rpc']['indexer_websocket_port']
    ret['rpc']['indexer_websocket_uri'] = f'ws://{ips[5]}:{indexer_ws_port}/evm'

    return ret
