#!/usr/bin/env python3

import os
import sys
import logging

from pathlib import Path

import click
import requests

from ..config import *

from .cli import cli


@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--loglevel', default='info',
    help='Provide logging level. Example --loglevel debug, default=warning')
@click.option(
    '--target-dir', default='.',
    help='target')
def up(
    pid,
    loglevel,
    target_dir,
):
    """Bring tevmc daemon up.
    """
    from ..tevmc import TEVMController

    if Path(pid).resolve().exists():
        print('Daemon pid file exists. Abort.')
        sys.exit(1)

    fmt = logging.Formatter(
        fmt='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%H:%M:%S'
    )
    loglevel = loglevel.upper()
    logger = logging.getLogger('tevmc')
    logger.setLevel(loglevel)
    logger.propagate = False

    # config logging to stdout
    oh = logging.StreamHandler(sys.stdout)
    oh.setLevel(loglevel)
    oh.setFormatter(fmt)
    logger.addHandler(oh)

    with open(pid, 'w+') as pidfile:
        pidfile.write(str(os.getpid()))

    try:
        with TEVMController(
            logger=logger,
            root_pwd=target_dir
        ) as _tevmc:
            logger.critical('control point reached')
            try:
                _tevmc.serve_api()

            except KeyboardInterrupt:
                logger.warning('interrupt catched.')

    except requests.exceptions.ReadTimeout:
        logger.critical(
            'docker timeout! usually means system hung, '
            'please await tear down or run \'tevmc clean\''
            'to cleanup envoirment.')
