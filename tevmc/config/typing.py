#!/usr/bin/env python3

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union


class IniDict(BaseModel):
    wasm_runtime: str
    vm_oc_compile_threads: int
    vm_oc_enable: bool

    chain_state_size: int
    account_queries: bool
    abi_serializer_max_time: int

    http_addr: str
    allow_origin: str
    http_verbose_error: bool
    contracts_console: bool
    http_validate_host: bool
    p2p_addr: str
    p2p_max_nodes: int

    agent_name: str

    history_endpoint: str
    trace_history: bool
    chain_history: bool
    history_debug_mode: bool
    history_dir: str

    sync_fetch_span: int

    max_clients: int
    cleanup_period: Optional[int] = None
    allowed_connection: Optional[str] = None
    http_max_response_time: int
    http_max_body_size: Optional[int] = None

    enable_stale_production: Optional[bool] = None

    sig_provider: str

    disable_subjective_billing: bool
    max_transaction_time: int

    plugins: List[str]
    peers: List[str]
    subst: Union[str, Dict[str, str], None] = None

class DaemonDict(BaseModel):
    port: int
    testing: Optional[bool] = False
    wait_sync: Optional[bool] = None
    network: Optional[str] = None
    services: List[str]

class MountDict(BaseModel):
    source: str
    target: str
    mtype: str = Field('bind', alias='type')

class CommonDict(BaseModel):
    name: str
    tag: str
    docker_path: str
    build_path: str
    config_path: Optional[str] = None
    data_path: Optional[str] = None
    logs_path: Optional[str] = None
    mounts: Optional[List[MountDict]] = None
    virtual_ip: Optional[str] = None
    wait_startup: Optional[bool] = True
    show_startup: Optional[bool] = None
    show_build: Optional[bool] = False
    requires: List[str] = []

class RedisDict(CommonDict):
    host: str
    port: int

class ElasticsearchDict(CommonDict):
    protocol: str
    port: int

class KibanaDict(CommonDict):
    host: str
    port: int

class NodeosDict(CommonDict):
    data_path_guest: str
    contracts_dir: str
    genesis: Optional[str] = None
    snapshot: Optional[str] = None
    logs_file: str
    v2_api: str
    nodeos_bin: str
    eosio_evm: Optional[str] = Field(None, alias='eosio.evm')
    space_monitor: bool
    produce: bool
    initialize: bool
    api_check: bool
    ini: IniDict

class TranslatorDict(CommonDict):
    start_block: Union[int, str] = 'override'
    deploy_block: Union[int, str] = 'override'
    evm_start_block: int
    evm_validate_hash: str
    stop_block: int
    prev_hash: str
    worker_amount: int
    elastic_dump_size: int
    elastic_timeout: int

class RpcDict(CommonDict):
    chain_id: int
    debug: bool
    api_host: str
    api_port: int
    remote_endpoint: str
    signer_account: str
    signer_permission: str
    signer_key: str
    contracts: Dict[str, str]
    indexer_websocket_host: str
    indexer_websocket_port: int
    indexer_websocket_uri: str
    websocket_host: str
    websocket_port: int
    elastic_prefix: str
    elasitc_index_version: str

class ConfigDict(BaseModel):
    daemon: DaemonDict
    redis: RedisDict
    elasticsearch: ElasticsearchDict
    kibana: KibanaDict
    nodeos: NodeosDict
    beats: CommonDict
    translator: TranslatorDict
    rpc: RpcDict
