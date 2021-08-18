#!/usr/bin/env python3


class RunfileFormatError(Exception):
    pass


class RunfileNotFoundError(Exception):
    def __init__(self, path):
        self.path = path


class TargetNotFoundError(Exception):
    def __init__(self, target=None):
        self.target = target


class TargetExecutionError(Exception):
    def __init__(self, exit_code):
        self.exit_code = exit_code


class CodeBlockExecutionError(Exception):
    def __init__(self, exit_code):
        self.exit_code = exit_code


class ContainerBuildError(Exception):
    def __init__(self, exit_code):
        self.exit_code = exit_code
