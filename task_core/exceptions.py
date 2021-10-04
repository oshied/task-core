#!/usr/bin/env python3
"""exception classess"""


class InvalidRole(Exception):
    """Exception if role is not defined"""


class InvalidService(Exception):
    """Exception if service is not defined"""


class ExecutionFailed(Exception):
    """Exception for execute failures"""


class InvalidFileData(Exception):
    """Exception for Invalid File data"""


class UnavailableException(Exception):
    """exception for unavailable conditions"""
