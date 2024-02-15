#!/usr/bin/env python3

import re
import subprocess
import time

from datetime import datetime
from typing import Optional

import requests

from tevmc.cleos_evm import CLEOSEVM
from tevmc.config.typing import NodeosDict

from . import DockerService, Mount


class Service(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: NodeosDict

        self.is_relaunch: bool = False

        self.cleos_url: str
        self.cleos_evm_url: str
        self.cleos: Optional[CLEOSEVM] = None

        self.logfile: str = ''
        self.api_port: int
        self.history_port: int

        self.producer_key: str

        self.startup_logs_kwargs = {
            'from_latest': True,
            'timeout': 5 * 60
        }

        self.template_whitelist = [
            ('docker/nodeos/build/Dockerfile', 'build/Dockerfile'),
            ('config/logrotate.conf', 'config/logrotate.conf'),
            ('config/nodeos.config.ini', 'nodeos.config.ini'),
            ('config/nodeos.local.config.ini', 'nodeos.local.config.ini')
        ]

    @property
    def startup_phrase(self) -> Optional[str]:
        if not self.config.wait_startup:
            return None

        if not self.is_relaunch:
            return 'Done storing initial state on startup'

        else:
            if self.config.produce:
                return 'Produced block'

            else:
                return 'Received block'

    def configure(self):
        self.is_relaunch = (self.data_dir / 'blocks').is_dir()

        self.logfile = f'/logs/{self.config.logs_file}'

        self.api_port = int(self.config.ini.http_addr.split(':')[1])
        self.history_port = int(self.config.ini.history_endpoint.split(':')[1])

        self.config_subst.update({
            'timestamp': str(datetime.now()),
            'nodeos_port': self.api_port,
            'nodeos_log_path': self.logfile,
            'nodeos_history_port': self.history_port
        })

        self.config_subst.update(self.config.ini.model_dump())

        # normalize bools
        norm_subst = {}
        for key, val in self.config_subst.items():
            if isinstance(val, bool):
                norm_subst[key] = str(val).lower()
            else:
                norm_subst[key] = val

        ini_conf = self.templates[
            'nodeos.config.ini'].substitute(**norm_subst) + '\n'

        if self.tevmc.chain_type == 'local':
            ini_conf += self.templates[
                'nodeos.local.config.ini'].substitute(**norm_subst) + '\n'

        for plugin in norm_subst['plugins']:
            ini_conf += f'plugin = {plugin}' + '\n'

        if 'subst' in norm_subst:
            ini_conf += f'plugin = eosio::subst_plugin\n'
            ini_conf += '\n'
            sinfo = norm_subst['subst']
            if isinstance(sinfo, str):
                ini_conf += f'subst-manifest = {sinfo}'

            elif isinstance(sinfo, dict):
                for skey, val in sinfo.items():
                    ini_conf += f'subst-by-name = {skey}:{val}'

        ini_conf += '\n'

        for peer in norm_subst['peers']:
            ini_conf += f'p2p-peer-address = {peer}\n'

        with open(self.config_dir / 'config.ini', 'w+') as target_file:
            target_file.write(ini_conf)

        # remove templates that are related to nodeos.ini generation
        del self.templates['nodeos.config.ini']
        del self.templates['nodeos.local.config.ini']

        super().configure()

    def prepare(self):
        data_path_guest = self.config.data_path_guest
        contracts_dir = self.service_dir / self.config.contracts_dir

        self.mounts = [
            Mount('/root', str(self.config_dir.resolve()), 'bind'),
            Mount('/logs', str(self.logs_dir.resolve()), 'bind'),
            Mount('/opt/eosio/bin/contracts', str(contracts_dir.resolve()), 'bind'),
            Mount(data_path_guest, str(self.data_dir.resolve()), 'bind')
        ]

        if self.tevmc.network:
            self.more_params['ports'] = {
                f'{self.api_port}/tcp': self.api_port,
                f'{self.history_port}/tcp': self.history_port
            }
            self.more_params['mem_limit'] = '6g'

        # generate nodeos command
        nodeos_cmd = [
            self.config.nodeos_bin,
            '--config=/root/config.ini',
            f'--data-dir={self.config.data_path_guest}',
            '--disable-replay-opts',
            '--logconf=/root/logging.json'
        ]

        if not self.is_relaunch and not (self.data_dir / 'blocks/blocks.log').is_file():
            if self.config.snapshot:
                nodeos_cmd += [f'--snapshot={self.config.snapshot}']

            elif self.config.genesis:
                nodeos_cmd += [
                    f'--genesis-json=/root/genesis/{self.config.genesis}.json'
                ]

        if not self.config.space_monitor:
            nodeos_cmd += ['--resource-monitor-not-shutdown-on-threshold-exceeded']

        if self.config.produce:
            nodeos_cmd += ['-e', '-p', 'eosio']

        nodeos_cmd += ['>>', self.logfile, '2>&1']
        nodeos_cmd_str = ' '.join(nodeos_cmd)

        cmd = ['/bin/bash', '-c', nodeos_cmd_str]

        self.logger.tevmc_info(f'launching nodeos with cmd: \"{" ".join(cmd)}\"')

        self.more_params['command'] = cmd

    def start(self):
        # TODO: fix logrotate
        # docker_open_process(
        #     self.tevmc.client, self.container,
        #     ['/bin/bash', '-c',
        #         'while true; do logrotate /root/logrotate.conf; sleep 60; done'])

        self.cleos_url = f'http://{self.ip}:{self.api_port}'
        self.cleos_evm_url = f'http://{self.ip}:{self.tevmc.config.rpc.api_port}/evm'

        # setup cleos wrapper
        cleos = CLEOSEVM(
            self.tevmc.client,
            self.container,
            logger=self.logger,
            url=self.cleos_url,
            evm_url=self.cleos_evm_url,
            chain_id=self.tevmc.config.rpc.chain_id)

        self.cleos = cleos
        self.tevmc.cleos = cleos

        if self.tevmc.chain_type == 'local' and self.config.initialize:
            self.producer_key = self.config.ini.sig_provider.split(':')[-1]

            self.logger.tevmc_info('waiting on nodeos to produce a block...')

            # await for nodeos to produce a block
            output = cleos.wait_produced(from_file=self.logfile)
            cleos.wait_blocks(1)
            self.logger.tevmc_info('done')

            self.is_fresh = 'Initializing new blockchain with genesis state' in output

            if self.is_fresh:
                cleos.start_keosd(
                    '-c',
                    '/root/keosd_config.ini')

                cleos.setup_wallet(self.producer_key)
                self.logger.tevmc_info('wallet setup')

                self.logger.tevmc_info('performing chain boot sequence...')
                cleos.boot_sequence(
                    sys_contracts_mount='/opt/eosio/bin/contracts',
                    verify_hash=False)
                self.logger.tevmc_info('done')

                cleos.deploy_evm(self.config.eosio_evm)
                self.logger.tevmc_info('evm deployed')

                evm_deploy_block = cleos.evm_deploy_info['processed']['block_num']

                self.tevmc.config.translator.start_block = evm_deploy_block
                self.tevmc.config.translator.deploy_block = evm_deploy_block
                self.tevmc.update_configs()
                self.tevmc.write_config()

                self.cleos.create_test_evm_account()
                self.logger.tevmc_info('created evm test accounts')

        else:
            self.logger.tevmc_info('waiting on nodeos to receive a block...')
            cleos.wait_received(from_file=self.logfile)
            self.logger.tevmc_info('done')

        if self.config.api_check:
            # wait until nodeos apis are up
            for _ in range(60):
                try:
                    cleos.get_info()
                    break

                except requests.exceptions.ConnectionError:
                    self.logger.tevmc_error('connection error trying to get chain info...')
                    time.sleep(1)

        if not self.is_relaunch:
            start_block = int(self.tevmc.config.translator.start_block) - 1
            self.logger.tevmc_info(
                f'wait on nodeos to sync until evm start_block #{start_block}')

            current_head_block = int(cleos.get_info()['head_block_num'])
            remaining = start_block - current_head_block
            while remaining > 0:
                speed = self.measure_sync_speed(10)
                current_head_block = int(cleos.get_info()['head_block_num'])
                remaining = start_block - current_head_block
                self.logger.tevmc_info(f'{remaining} remaining, current speed: {speed} blocks/sec')

    def stream_logs(self, **kwargs):
        lines = (
            int(kwargs['lines'])
            if 'lines' in kwargs
            else 100
        )
        timeout = (
            int(kwargs['timeout'])
            if 'timeout' in kwargs
            else 60
        )

        if 'from_latest' in kwargs:
            lines = 0

        log_path = (
            self.logs_dir / self.config.logs_file).resolve()

        process = subprocess.Popen(
            ['bash', '-c',
                f'timeout {timeout}s tail -n {lines} -f {log_path}'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        for line in iter(process.stdout.readline, b''):
            msg = line.decode('utf-8')
            if 'clear_expired_input_' in msg:
                continue

            pattern = r'\S+\s+\S+\s+(.*)'
            match = re.search(pattern, msg)
            msg = match.group(1) if match else ''

            yield msg

        process.stdout.close()
        process.wait()

        if process.returncode != 0:
            raise ValueError(
                f'tail returned {process.returncode}\n'
                f'{process.stderr.read().decode("utf-8")}')

    def stop(self):
        if self.cleos and self.running:
            ec, out = self.run_process(['pkill', '-f', 'nodeos'])
            self.logger.tevmc_info(f'pkill: {ec} {out}')
            for log in self.stream_logs(lines=10):
                self.logger.tevmc_info(log.rstrip())
                if 'nodeos successfully exiting' in log:
                    break

        super().stop()

    def _get_remote_head_block(self):
        if 'testnet' in self.tevmc.chain_name:
            endpoint = 'https://testnet.telos.net'
        else:
            endpoint = 'https://mainnet.telos.net'

        resp = requests.get(f'{endpoint}/v1/chain/get_info').json()
        return int(resp['head_block_num'])

    def _get_latest_block_num(self) -> int:
        return self.cleos.get_info()['head_block_num']

    def measure_sync_speed(self, time_interval: float = 10) -> float:
        start_block = self._get_latest_block_num()
        time.sleep(time_interval)
        end_block = self._get_latest_block_num()

        blocks_synced = end_block - start_block
        speed = blocks_synced / time_interval

        return speed
