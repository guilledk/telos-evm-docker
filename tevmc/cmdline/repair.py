#!/usr/bin/env python3

import logging

from pathlib import Path

import click

from tevmc.testing.database import ElasticDataEmptyError, perform_data_repair

from .cli import cli


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Path to config file.')
def repair(config):
    try:
        perform_data_repair(Path(config))

    except ElasticDataEmptyError:
        logging.info('no data to repair')
