#!/usr/bin/env python3

import docker
import hashlib
import os
import re
import time
from runfile.util import duration, human_time_to_seconds, msg, MsgType, \
    to_plaintext
from runfile.exceptions import CodeBlockExecutionError, TargetExecutionError, \
    RunfileFormatError, ContainerBuildError
from runfile.cache import RunfileCache
from io import BytesIO


class Target():
    pattern = (r'^\#\#\s+(?P<name>.+?)'
               r'(?:\n+(?P<desc>[^\#\n].+?))?\n(?=\n|`|#|$)')

    def __init__(self, orig=None, name=None, desc=None):
        self.orig = orig
        self.name = name
        self.unique_name = None
        self.orig_desc = desc
        self.desc = to_plaintext(desc)
        self.blocks = []
        self.runfile = None
        self.config = {}
        self.dockerfile = None
        self.container = None

        self.validate()

    def __str__(self):
        s = f"## {self.name}"
        if self.desc:
            s += f"\n\n{self.orig_desc}"
        s += "\n"
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
        self.result.target_start = time.time()
        if not self.name:
            self.result.common = True

        if self.runfile.use_containers:
            if self.dockerfile:
                try:
                    self.build_container()
                    self.result.set_status(TargetResult.SUCCESS)
                except ContainerBuildError as e:
                    self.result.exception = e
                    self.result.set_status(TargetResult.FAILURE)
                    return self.result
            else:
                self.container = self.runfile.container()

        if not self.blocks:
            if self.config and self.name:
                # Technically, we executed the config, so mark success
                self.result.set_status(TargetResult.SUCCESS)
            return self.result

        if not self.is_expired():
            self.result.set_status(TargetResult.CACHED)
            return self.result

        style = MsgType.CONTAINER if self.container else MsgType.WORKING
        msg(f'Running {self.unique_name}...', style)

        try:
            for block in self.blocks:
                block.execute(self.container)
            self.result.set_status(TargetResult.SUCCESS)
        except CodeBlockExecutionError as e:
            self.result.exception = e
            self.result.set_status(TargetResult.FAILURE)

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
        msg(f'Building container for {self.unique_name}...',
            MsgType.WORKING)

        build_error = None
        try:
            image = client.images.build(
                fileobj=build_file,
                rm=True
            )[0]
        except docker.errors.BuildError as e:
            build_error = e
            print(str(build_error))
            print(
                f'Failed building container for {self.unique_name}.',
                MsgType.FAILURE)
            print()

        if build_error:
            raise ContainerBuildError(255)

        msg('Container built.', MsgType.CONTAINER)
        print()
        self.cache()['image'] = image.id
        self.cache()['build_file'] = df_hash
        self.start_container(image)

    # TODO: Get other volumes from target config, if applicable
    # TODO: Inspect image for workdir and default to /work
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
        self.common = False
        self.root = False

    def __bool__(self):
        return self.status is not None

    def print_status(self):
        if self.status == TargetResult.SUCCESS:
            msg(f'Completed {self.name}.',
                MsgType.SUCCESS,
                suffix=f'({self.time()})')
        elif self.status == TargetResult.FAILURE:
            msg(f'Failed {self.name}.',
                MsgType.FAILURE,
                suffix=f'({self.time()})')
        elif self.status == TargetResult.CACHED:
            msg(f'Used cache for {self.name}.', MsgType.CACHE)

    def time(self):
        return duration(self.target_start, self.target_finish)

    def raise_if_failed(self):
        if self.status == TargetResult.FAILURE:
            raise TargetExecutionError(self.exception.exit_code)

    def set_status(self, status):
        self.target_finish = time.time()
        self.status = status
