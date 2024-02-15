#!/usr/bin/env python3

import time

import pytest

from tevmc.testing.database import ElasticDriver


@pytest.mark.services('elastic', 'nodeos', 'indexer')
def test_indexer_reconnect(tevmc_local):
    tevmc = tevmc_local

    for msg in tevmc.stream_logs('translator', from_latest=True):
        tevmc.logger.info(msg.rstrip())
        if 'drained' in msg:
            break

    tevmc.restart_service('nodeos')

    for msg in tevmc.stream_logs('translator', from_latest=True):
        tevmc.logger.info(msg.rstrip())
        if 'drained' in msg:
            break

    elastic = ElasticDriver(tevmc.config.model_dump())
    elastic.full_integrity_check()
