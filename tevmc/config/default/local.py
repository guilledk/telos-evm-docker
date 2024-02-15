#!/usr/bin/env python3

daemon = {
    'port': 12321,
    'services': [
        'redis',
        'elastic',
        'nodeos',
        'translator',
        'rpc'
    ]
}

redis = {
    'name': 'redis',
    'docker_path': 'redis',
    'build_path': 'build',
    'config_path': 'config',
    'data_path': 'data',
    'tag': 'tevm:redis',
    'host': '127.0.0.1',
    'port': 6379
}

elasticsearch = {
    'name': 'elasticsearch',
    'docker_path': 'elasticsearch',
    'build_path': 'build',
    'data_path': 'data',
    'logs_path': 'logs',
    'tag': 'tevm:elasticsearch',
    'protocol':  'http',
    'port': 9200,
}

kibana = {
    'name': 'kibana',
    'docker_path': 'kibana',
    'build_path': 'build',
    'config_path': 'config',
    'data_path': 'data',
    'tag': 'tevm:kibana',
    'host': '0.0.0.0',
    'port': 5601,
}

nodeos = {
    'name': 'nodeos',
    'tag': 'tevm:nodeos-4.0.4-evm',
    'docker_path': 'nodeos',
    'build_path': 'build',
    'data_path_guest': '/mnt/dev/data',
    'data_path': 'data',
    'config_path': 'config',
    'logs_path': 'logs',
    'contracts_dir': 'contracts',
    'genesis': 'local',
    'logs_file': 'nodeos.log',
    'v2_api': 'disabled',
    'nodeos_bin': 'nodeos',
    'eosio.evm': '/opt/eosio/bin/contracts/eosio.evm/receiptless',
    'space_monitor': True,
    'produce': True,
    'initialize': True,
    'api_check': True,
    'show_startup': True,
    'ini': {
        'wasm_runtime': 'eos-vm-jit',
        'vm_oc_compile_threads': 4,
        'vm_oc_enable': True,

        'chain_state_size': 65536,
        'abi_serializer_max_time': 2000000,
        'account_queries': True,

        'http_addr': '0.0.0.0:8888',
        'allow_origin': '*',
        'http_verbose_error': True,
        'contracts_console': True,
        'http_validate_host': False,
        'p2p_addr': '0.0.0.0:9876',
        'p2p_max_nodes': 1,

        'agent_name': 'Telos Local Testnet',

        'history_endpoint': '0.0.0.0:29999',
        'trace_history': True,
        'chain_history': True,
        'history_debug_mode': True,
        'history_dir': 'state-history',

        'sync_fetch_span': 1600,

        'max_clients': 250,
        'cleanup_period': 30,
        'allowed_connection': 'any',
        'http_max_response_time': 100000,
        'http_max_body_size': 100000000,

        'enable_stale_production': True,

        'sig_provider': 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L=KEY:5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',

        'disable_subjective_billing': True,
        'max_transaction_time': 500,

        'plugins': [
            'eosio::http_plugin',
            'eosio::chain_plugin',
            'eosio::chain_api_plugin',
            'eosio::net_plugin',
            'eosio::producer_plugin',
            'eosio::producer_api_plugin',
            'eosio::state_history_plugin'
        ],
        'peers': [],
        'subst': {
            'eosio.evm': '/opt/eosio/bin/contracts/eosio.evm/regular/regular.wasm'
        }
    }
}

beats = {
    'name': 'beats',
    'tag': 'tevm:beats',
    'build_path': 'build',
    'docker_path': 'beats',
    'config_path': 'config',
    'data_path': 'data'
}

translator = {
    'name': 'translator',
    'tag': 'tevm:translator',
    'docker_path': 'translator',
    'build_path': 'build',
    'show_startup': True,
    'start_block': 'override',
    'evm_start_block': -1,
    'evm_validate_hash': '',
    'stop_block': 4294967295,
    'deploy_block': 'override',
    'prev_hash': '',
    'worker_amount': 1,
    'elastic_dump_size': 1,
    'elastic_timeout': 1000 * 60 * 1
}

rpc = {
    'name': 'rpc',
    'tag': 'tevm:rpc',
    'docker_path': 'rpc',
    'build_path': 'build',
    'logs_path': 'logs',
    'show_startup': True,
    'chain_id': 41,
    'debug': True,
    'api_host': '0.0.0.0',
    'api_port': 7000,
    'remote_endpoint': 'http://127.0.0.1:7000/evm',
    'signer_account': 'rpc.evm',
    'signer_permission': 'active',
    'signer_key': '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL',
    'contracts': {
        'main': 'eosio.evm'
    },
    'indexer_websocket_host': '0.0.0.0',
    'indexer_websocket_port': '7300',
    'indexer_websocket_uri': 'ws://127.0.0.1:7300/evm',
    'websocket_host': '0.0.0.0',
    'websocket_port': 7400,
    'elastic_prefix': 'telos-local',
    'elasitc_index_version': 'v1.5'
}

default_config = {
    'daemon': daemon,

    'redis': redis,
    'elasticsearch': elasticsearch,
    'kibana': kibana,
    'nodeos': nodeos,
    'beats': beats,
    'translator': translator,
    'rpc': rpc
}
