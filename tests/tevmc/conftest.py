#!/usr/bin/env python3

import os

import pytest
import docker
import logging
import requests

from contextlib import contextmanager

from tevmc import TEVMController
from tevmc.config import (
    local, testnet, mainnet,
    build_docker_manifest,
    randomize_conf_ports,
    randomize_conf_creds
)
from tevmc.cmdline.init import touch_node_dir
from tevmc.cmdline.build import perform_docker_build
from tevmc.cmdline.clean import clean
from tevmc.cmdline.cli import get_docker_client


@contextmanager
def bootstrap_test_stack(tmp_path_factory, config, randomize=True, **kwargs):
    if randomize:
        config = randomize_conf_ports(config)
        config = randomize_conf_creds(config)

    client = get_docker_client()

    chain_name = config['hyperion']['chain']['name']

    tmp_path = tmp_path_factory.getbasetemp() / chain_name
    manifest = build_docker_manifest(config)

    tmp_path.mkdir(parents=True, exist_ok=True)
    touch_node_dir(tmp_path, config, 'tevmc.json')
    perform_docker_build(
        tmp_path, config, logging)

    try:
        with TEVMController(
            config,
            root_pwd=tmp_path,
            **kwargs
        ) as _tevmc:
            yield _tevmc

    except BaseException:
        pid = os.getpid()

        client = get_docker_client(timeout=10)

        containers = []
        for name, conf in config.items():
            if 'name' in conf:
                containers.append(f'{conf["name"]}-{pid}')


        containers.append(
            f'{local.default_config["hyperion"]["indexer"]["name"]}-{pid}')
        containers.append(
            f'{local.default_config["hyperion"]["api"]["name"]}-{pid}')

        for val in containers:
            while True:
                try:
                    container = client.containers.get(val)
                    container.stop()

                except docker.errors.APIError as err:
                    if 'already in progress' in str(err):
                        time.sleep(0.1)
                        continue

                except requests.exceptions.ReadTimeout:
                    print('timeout!')

                except docker.errors.NotFound:
                    print(f'{val} not found!')

                break
        raise


@pytest.fixture(scope='module')
def tevmc_local(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, local.default_config) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_local_non_rand(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, local.default_config, randomize=False) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_testnet(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, testnet.default_config) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_testnet_no_wait(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, testnet.default_config, wait=False) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_mainnet(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, mainnet.default_config) as tevmc:
        yield tevmc


@pytest.fixture(scope='module')
def tevmc_mainnet_no_wait(tmp_path_factory):
    with bootstrap_test_stack(
        tmp_path_factory, mainnet.default_config, wait=False) as tevmc:
        yield tevmc


from web3 import Web3


@pytest.fixture(scope='module')
def local_w3(tevmc_local):
    tevmc = tevmc_local
    hyperion_api_port = tevmc.config["hyperion"]["api"]["server_port"]
    eth_api_endpoint = f'http://localhost:{hyperion_api_port}/evm'

    w3 = Web3(Web3.HTTPProvider(eth_api_endpoint))
    assert w3.is_connected()

    yield w3
