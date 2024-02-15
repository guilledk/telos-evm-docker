#!/usr/bin/env python3

import sys
import tarfile

import pytest

from shutil import copyfile
from pathlib import Path
from contextlib import contextmanager

from web3 import Web3
from tevmc.cmdline.init import touch_conf

from tevmc.config import (
    randomize_conf_ports,
    add_virtual_networking
)

TEST_SERVICES = ['redis', 'elastic', 'nodeos', 'indexer', 'rpc']


def maybe_get_marker(request, mark_name: str, field: str, default):
    mark = request.node.get_closest_marker(mark_name)
    if mark is None:
        return default
    else:
        return getattr(mark, field)


def get_marker(request, mark_name: str, field: str):
    mark = maybe_get_marker(request, mark_name, field, None)
    if mark is None:
        raise ValueError(
            f'{mark_name} mark required, did you forgot to mark the test?')
    else:
        return mark


@contextmanager
def bootstrap_test_stack(request, tmp_path_factory, capsys):
    from tevmc import TEVMController
    config = get_marker(request, 'config', 'kwargs')

    custom_subst_abi = maybe_get_marker(
        request, 'custom_subst_abi', 'args', [None])[0]
    custom_subst_wasm = maybe_get_marker(
        request, 'custom_subst_wasm', 'args', [None])[0]
    custom_nodeos_tar = maybe_get_marker(
        request, 'custom_nodeos_tar', 'args', [None])[0]

    randomize = maybe_get_marker(request, 'randomize', 'args', [True])[0]

    if randomize:
        config = randomize_conf_ports(config)

    config['daemon']['services'] = maybe_get_marker(
        request, 'services', 'args', TEST_SERVICES
    )

    if sys.platform == 'darwin':
        config = add_virtual_networking(config)

    chain_name = config['rpc']['elastic_prefix']

    tmp_path = tmp_path_factory.getbasetemp() / chain_name
    tmp_path.mkdir(parents=True, exist_ok=True)

    if custom_subst_wasm:
        copyfile(
            custom_subst_wasm,
            tmp_path / 'docker/nodeos/contracts/eosio.evm/regular/regular.wasm'
        )

    if custom_subst_abi:
        copyfile(
            custom_subst_abi,
            tmp_path / 'docker/nodeos/contracts/eosio.evm/regular/regular.abi'
        )

    if custom_nodeos_tar:
        tar_path = Path(custom_nodeos_tar)
        extensionless_path = Path(tar_path.stem).stem

        bin_name = str(extensionless_path)

        host_config_path = tmp_path / 'docker/nodeos/config'
        host_config_path.mkdir(parents=True, exist_ok=True)

        with tarfile.open(custom_nodeos_tar, 'r:gz') as file:
            file.extractall(path=host_config_path)

        binary = f'{bin_name}/usr/local/bin/nodeos'

        assert (host_config_path / binary).is_file()

        config['nodeos']['nodeos_bin'] = '/root/' + binary

    config['daemon']['testing'] = True
    touch_conf(tmp_path / 'tevmc.json', config)

    with capsys.disabled():
        print()
        with TEVMController(root_pwd=tmp_path) as _tevmc:
            yield _tevmc


@pytest.fixture
def tevm_node(request, tmp_path_factory, capsys):
    with bootstrap_test_stack(request, tmp_path_factory, capsys) as tevmc:
        yield tevmc


def open_web3(tevm_node):
    rpc_api_port = tevm_node.config.rpc.api_port
    rpc_ip = tevm_node.network_ip('rpc')
    eth_api_endpoint = f'http://{rpc_ip}:{rpc_api_port}/evm'

    w3 = Web3(Web3.HTTPProvider(eth_api_endpoint))
    assert w3.is_connected()

    return w3


def open_websocket_web3(tevm_node):
    rpc_ws_port = tevm_node.config.rpc.websocket_port
    rpc_ip = tevm_node.services.rpc.ip
    eth_ws_endpoint = f'ws://{rpc_ip}:{rpc_ws_port}/evm'

    w3 = Web3(Web3.WebsocketProvider(eth_ws_endpoint))
    assert w3.is_connected()

    return w3
