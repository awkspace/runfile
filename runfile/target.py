#!/usr/bin/env python3

import docker
import hashlib
import os
import re
import time
from runfile.util import duration, human_time_to_seconds
from runfile.exceptions import CodeBlockExecutionError, TargetExecutionError, \
    RunfileFormatError
from runfile.cache import RunfileCache
from io import BytesIO


class Target():
    pattern = r'^\#\#\s+(?P<name>.+?)(?:\n+(?P<desc>[^\#\n].+?))?$'

    def __init__(self, orig=None, name=None, desc=None):
        self.orig = orig
        self.name = name
        self.unique_name = None
        self.desc = desc
        self.blocks = []
        self.runfile = None
        self.config = {}
        self.dockerfile = None
        self.container = None

        self.validate()

    def __str__(self):
        s = f"## {self.name}"
        if self.desc:
            s += f"\n\n{self.desc}"
        return s

    def __repr__(self):
        return f'Target({self.name},{self.desc})'

    def __eq__(self, other):
        if not isinstance(other, Target):
            return False
        if self.name != other.name:
            return False
        if self.desc != other.desc:
            return False
        return True

    def __hash__(self):
        return hash((self.runfile, self.name))

    def validate(self):
        if self.name:
            name_pattern = r'^[A-Za-z0-9_]+$'
            if not re.match(name_pattern, self.name):
                raise RunfileFormatError(
                    f'Target name "{self.name}" '
                    'can only contain alphanumeric characters and '
                    'underscores.')

    def execute(self, silent=False):
        self.result = TargetResult(self.unique_name)
        if not self.name:
            self.result.setup = True

        if self.runfile.use_containers:
            if self.dockerfile:
                self.build_container()
            else:
                self.container = self.runfile.container()

        if not self.is_expired():
            self.result.status = TargetResult.CACHED
            return self.result

        self.result.target_start = time.time()
        icon = '⏳'
        if self.container:
            icon = '📦'
        action = 'Executing target'
        if not self.name:
            action = 'Setting up'
        print(f'{icon} {action} {self.unique_name}...')

        try:
            for block in self.blocks:
                block.execute(self.container)
            self.result.status = TargetResult.SUCCESS
        except CodeBlockExecutionError as e:
            self.result.exception = e
            self.result.status = TargetResult.FAILURE

        self.result.target_finish = time.time()
        if self.name and self.container != self.runfile.container():
            self.stop_container()
        if self.result.status == TargetResult.SUCCESS:
            self.cache()['last_run'] = self.result.target_finish
            self.cache()['body'] = self.body_hash()
            if 'invalidates' in self.config:
                for target_expr in self.config['invalidates']:
                    for target in self.runfile.find_target(target_expr):
                        target.clear_cache()

        return self.result

    def cache(self):
        cache = RunfileCache()
        return cache['targets'][self.cache_key()]

    def clear_cache(self):
        cache = RunfileCache()
        if self.cache_key() in cache['targets']:
            del cache['targets'][self.cache_key()]

    def cache_key(self):
        h = hashlib.sha1()
        header = self.runfile.header
        h.update(self.runfile.path.encode('utf-8'))
        for include in header.include_path:
            h.update(include['path'].encode('utf-8'))
        if self.name:
            h.update(self.name.encode('utf-8'))
        return h.hexdigest()[:7]

    def is_expired(self):
        if not self.cache()['last_run']:
            return True  # Need to run to have something to cache
        if self.cache()['body'] != self.body_hash():
            return True  # Code changed

        for subtarget_expr in self.config.get('requires', []):
            subtargets = self.runfile.find_target(subtarget_expr)
            for subtarget in subtargets:
                if subtarget.cache()['last_run'] > self.cache()['last_run']:
                    return True

        expires = human_time_to_seconds(self.config.get('expires', '0'))
        if expires is None or expires < 0:
            return False  # Cache indefinitely

        return self.cache()['last_run'] + expires < time.time()

    def body_hash(self):
        h = hashlib.sha1()
        for block in self.blocks:
            h.update(block.body.encode('utf-8'))
        return h.hexdigest()

    def build_container(self):
        client = docker.from_env()
        df_hash = hashlib.sha1(self.dockerfile.encode('utf-8')).hexdigest()
        if self.cache()['image'] and self.cache()['build_file'] == df_hash:
            try:
                image = client.images.get(self.cache()['image'])
                return self.start_container(image)
            except docker.errors.ImageNotFound:
                pass
        build_file = BytesIO(self.dockerfile.encode('utf-8'))
        print(f'⏳ Building container for {self.unique_name}...')
        image = client.images.build(
            fileobj=build_file,
            rm=True
        )[0]
        print('📦 Container built.')
        print()
        self.cache()['image'] = image.id
        self.cache()['build_file'] = df_hash
        self.start_container(image)

    def start_container(self, image):
        client = docker.from_env()
        self.container = client.containers.run(
            image,
            command='/bin/cat',
            tty=True,
            detach=True,
            working_dir='/work',
            volumes={
                os.getcwd(): {
                    'bind': '/work',
                    'mode': 'rw'
                },
                '/tmp': {
                    'bind': '/mnt/tmp',
                    'mode': 'rw'
                }
            }
        )

    def stop_container(self):
        self.container.exec_run(f'chown -R {os.getuid()}:{os.getgid()} /work')
        self.container.kill()


class TargetResult():
    SUCCESS = 0
    FAILURE = 1
    CACHED = 2

    def __init__(self, name):
        self.name = name
        self.status = None
        self.target_start = None
        self.target_finish = None
        self.used_cache = False
        self.setup = False

    def __bool__(self):
        return self.status is not None

    def print_status(self):
        if not self.name:
            return
        if self.setup and self.status == TargetResult.SUCCESS:
            print(f'✅ Set up {self.name}. ({self.time()})')
        elif self.setup and self.status == TargetResult.FAILURE:
            print(f'❌ Failed setting up {self.name}. ({self.time()})')
        elif self.status == TargetResult.SUCCESS:
            print(f'✅ Completed {self.name}. ({self.time()})')
        elif self.status == TargetResult.FAILURE:
            print(f'❌ Failed {self.name}. ({self.time()})')
        elif self.status == TargetResult.CACHED:
            print(f'💾 Used cache for {self.name}')

    def time(self):
        return duration(self.target_start, self.target_finish)

    def raise_if_failed(self):
        if self.status == TargetResult.FAILURE:
            raise TargetExecutionError(self.exception.exit_code)
