#!/usr/bin/env python3
"""logging util functions"""

import logging

LOG = logging.getLogger(__name__)


def setup_basic_logging(debug=False):
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)s] %(message)s", level=log_level
    )
    LOG.debug("Logging setup")
