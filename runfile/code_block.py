#!/usr/bin/env python3

import os
from tempfile import TemporaryDirectory
from runfile.exceptions import CodeBlockExecutionError

language_info = {
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

    def execute(self):
        with TemporaryDirectory() as directory:
            filename = language_info.get(self.language, {}).get('file', 'run')
            filepath = os.path.join(directory, filename)
            with open(filepath, 'w') as f:
                f.write(self.body)
                f.flush()
                cmd = language_info.get(self.language, {}).get(
                    'cmd',
                    '/usr/bin/env {exe} "{file}"'
                )
                exit_code = os.system(
                    cmd.format(
                        dir=directory,
                        file=filepath,
                        exe=self.language
                    )
                )
                if exit_code:
                    raise CodeBlockExecutionError(exit_code)