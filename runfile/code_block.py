#!/usr/bin/env python3

import docker
import os
import shlex
import sys
from runfile.cache import RunfileCache
from runfile.exceptions import CodeBlockExecutionError
from subprocess import Popen, PIPE, STDOUT
from tempfile import TemporaryDirectory

language_info = {
    'sh': {
        'cmd': '/usr/bin/env sh -e "{file}"'
    },
    'bash': {
        'cmd': '/usr/bin/env bash -e "{file}"'
    },
    'zsh': {
        'cmd': '/usr/bin/env zsh -e "{file}"'
    },
    'js': {
        'cmd': '/usr/bin/env node "{file}"'
    },
    'go': {
        'file': 'run.go',
        'cmd': '/usr/bin/env go run "{dir}/run.go"'
    },
    'java': {
        'file': 'Main.java'
    },
    'c': {
        'file': 'run.c',
        'cmd': 'gcc "{dir}/run.c" -o "{dir}/run" && "{dir}/run"'
    },
    'cpp': {
        'file': 'run.cpp',
        'cmd': 'g++ "{dir}/run.cpp" -o "{dir}/run" && "{dir}/run"'
    },
    'csharp': {
        'file': 'run.cs',
        'cmd': 'mcs "{dir}/run.cs" && mono "{dir}/run.exe"'
    }
}


class CodeBlock():
    pattern = r'^```(?P<language>.+?)\s?\n(?P<body>.+?)\n```$'

    def __init__(self, orig=None, language=None, body=None):
        self.orig = orig
        self.language = language
        self.body = body

    def __str__(self):
        return f"```{self.language}\n{self.body}\n```"

    def __repr__(self):
        return f'CodeBlock({self.language}, {self.body})'

    def __eq__(self, other):
        if not isinstance(other, CodeBlock):
            return False
        if self.language != other.language:
            return False
        if self.body != other.body:
            return False
        return True

    def execute(self, container=None):
        cache = RunfileCache()
        for key, value in cache['vars'].items():
            os.environ[key] = value
        with TemporaryDirectory() as directory:
            filename = language_info.get(self.language, {}).get('file', 'run')
            filepath = os.path.join(directory, filename)
            with open(filepath, 'w') as f:
                f.write(self.body)
                f.flush()

            if container:
                directory = os.path.join('/mnt', directory[1:])
                filepath = os.path.join('/mnt', filepath[1:])

            cmd = language_info.get(self.language, {}).get(
                'cmd',
                '/usr/bin/env {exe} "{file}"')
            fmtcmd = cmd.format(
                dir=directory,
                file=filepath,
                exe=self.language
            )

            if container:
                exit_code = self.execute_in_container(fmtcmd, container)
            else:
                exit_code = self.execute_in_subprocess(fmtcmd)

            if exit_code:
                raise CodeBlockExecutionError(exit_code)

    def execute_in_subprocess(self, cmd):
        trailing_byte = b''
        exit_code = None
        with Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT) as proc:
            while True:
                exit_code = proc.poll()
                if exit_code is not None:
                    read_bytes = proc.stdout.read()
                else:
                    read_bytes = proc.stdout.read(1)
                if read_bytes:
                    trailing_byte = read_bytes[-1:]
                sys.stdout.buffer.write(read_bytes)
                sys.stdout.buffer.flush()
                if exit_code is not None:
                    break

        if trailing_byte != b"\n":
            print()

        return exit_code

    def execute_in_container(self, cmd, container):
        client = docker.from_env()
        resp = client.api.exec_create(container.id, cmd)
        exec_result = client.api.exec_start(resp['Id'], stream=True)

        trailing_byte = b''
        for output in exec_result:
            trailing_byte = output[-1:]
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()

        if trailing_byte != b"\n":
            print()

        inspect = client.api.exec_inspect(resp['Id'])
        return inspect['ExitCode']
