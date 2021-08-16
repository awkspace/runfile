#!/usr/bin/env python3

import logging
import os
import re
import requests
import time
import yaml
from collections import OrderedDict
from colorama import Fore
from fnmatch import fnmatch
from graphlib import CycleError, TopologicalSorter
from runfile.code_block import CodeBlock
from runfile.exceptions import TargetNotFoundError, \
    RunfileFormatError, RunfileNotFoundError
from runfile.target import Target, TargetResult
from runfile.util import duration

logging.basicConfig()
logger = logging.getLogger('runfile')


class Runfile():
    def __init__(self, path):
        self.path = path
        self.header = None
        self.tokens = []
        self.children = OrderedDict()
        self.start_time = None
        self.results = []
        self.use_containers = False

    def __str__(self):
        tokens = [str(t) for t in self.tokens]
        s = ''.join(tokens)
        s = re.sub(r'\n*$', "\n\n", s, count=1)
        for _, rf in self.children.items():
            s += str(rf)
        s = re.sub(r'\n*$', "\n", s, count=1)
        return s

    def __hash__(self):
        return hash(self.header)

    def read_file(self):
        with open(self.path, 'r') as f:
            return f.read()

    def write_file(self, content):
        with open(self.path, 'w') as f:
            f.write(content)

    def append_file(self, content):
        with open(self.path, 'a') as f:
            f.write(content)

    def save(self):
        self.write_file(str(self))

    def load(self):
        self.tokenize()

    def is_file(self):
        return not re.search('https?://')

    def content(self):
        if os.path.exists(self.path):
            return self.read_file()

        if re.search('https?://', self.path):
            r = requests.get(self.path)
            if r.status_code == 200:
                return r.text

        raise RunfileNotFoundError(self.path)

    def tokenize(self):
        all_tokens = [self.content(), None]
        for element in [CodeBlock, RunfileHeader, Target]:
            i = 0
            while i < len(all_tokens):
                chunk = all_tokens[i]
                if not isinstance(chunk, str):
                    i += 1
                    continue
                match = re.search(
                    element.pattern, chunk, flags=re.MULTILINE | re.DOTALL)
                if match:
                    del all_tokens[i]
                    if match.span()[0] > 0:
                        all_tokens.insert(i, chunk[:match.span()[0]])
                        i += 1
                    all_tokens.insert(
                        i, element(orig=match.group(), **match.groupdict()))
                    i += 1
                    if match.span()[1] < len(chunk):
                        all_tokens.insert(i, chunk[match.span()[1]:])
                else:
                    i += 1

        rf = self
        for token in all_tokens:
            if rf.header and isinstance(token, RunfileHeader) or token is None:
                # Reached the end of the current Runfile
                rf.parse()
            if isinstance(token, RunfileHeader):
                if rf.header:
                    if not token.include_path and rf is self:
                        raise RunfileFormatError(
                            'Only one top-level header is permitted '
                            'per Runfile.')
                    rf = self
                    for include in token.include_path:
                        child = rf.child_name(include['path'])
                        if not child:
                            child = include['name']
                        if child not in rf.children:
                            rf.children[child] = Runfile(child)
                        rf = rf.children[child]
                        rf.header = token
                else:
                    rf.header = token
            elif rf is self and not rf.header:
                raise RunfileFormatError('Missing Runfile header.')
            if token is not None:
                rf.tokens.append(token)

        self.ensure_includes()
        self.name_targets()

    def parse(self):
        self.targets = {None: Target(None, None)}
        target = self.targets[None]
        target.runfile = self

        for token in self.tokens:
            if isinstance(token, Target):
                target = token
                if target.name in self.targets:
                    raise RunfileFormatError(
                        f'Duplicate target name: {target.name}')
                self.targets[target.name] = target
                target.runfile = self
            elif isinstance(token, CodeBlock):
                if token.language == 'yaml':
                    target.config = yaml.load(
                        token.body, Loader=yaml.SafeLoader)
                elif token.language == 'dockerfile':
                    target.dockerfile = token.body
                else:
                    target.blocks.append(token)

    def includes(self):
        meta_target = self.targets[None]
        if not meta_target.config:
            return OrderedDict()
        include_list = meta_target.config.get('includes', [])
        includes = OrderedDict()
        for include in include_list:
            keys = list(include)
            if len(keys) > 1:
                raise RunfileFormatError(
                    'Includes must contain one key.')
            key = keys[0]
            includes[key] = include[key]
        return includes

    def ensure_includes(self):
        for key in list(self.children):
            if key not in self.includes():
                del self.children[key]
                continue
            child_path = self.children[key].header.include_path[0]['path']
            if child_path != self.includes()[key]:
                del self.children[key]

        for i in range(len(list(self.includes()))):
            key = list(self.includes())[i]
            do_import = False
            if len(self.children) < i+1:
                do_import = True
            else:
                child_key = list(self.children)[i]
                if key != child_key:
                    do_import = True

            if do_import:
                self.children[key] = Runfile(self.includes()[key])
                self.children[key].load()
                self.children[key].prepend_include_path({
                    'name': key,
                    'path': self.includes()[key]
                })

    def child_name(self, path):
        if not self.includes():
            return None
        for key, value in self.includes().items():
            if value == path:
                return key

    def name_targets(self, all_targets=None):
        if all_targets is None:
            all_targets = []
        for _, target in self.targets.items():
            include_path = target.runfile.header.include_path
            if target.name is None:
                if include_path:
                    target.unique_name = '/'.join(
                        [i['name'] for i in include_path])
                    continue
                else:
                    target.unique_name = self.path
                    continue
            name = target.name
            for include in reversed(include_path):
                if name in all_targets:
                    name = f'{include["name"]}/{name}'
                else:
                    break
            target.unique_name = name
            all_targets.append(target.unique_name)
        for child in self.children:
            self.children[child].name_targets(all_targets)

    def find_target(self, target_expr):
        targets = []
        for target_name, target in self.targets.items():
            if not target_name:
                continue
            if fnmatch(target_name, target_expr):
                targets.append(target)
        if targets and '**' not in target_expr:
            return targets

        if '/' in target_expr:
            child_name, target_expr = target_expr.split('/', 1)
            if child_name in self.children:
                return self.children[child_name].find_target(target_expr)

        for _, child in self.children.items():
            targets += child.find_target(target_expr)

        return targets

    def execute_target(self, target_expr):
        if not self.start_time:
            self.start_time = time.time()

        graph = {}
        for target in self.find_target(target_expr):
            graph.update(self.graph_dependencies(target))
            if target not in graph:
                graph[target] = set()
            graph[target].add(target.runfile.targets[None])

        ts = TopologicalSorter(graph)
        cycle_error = None
        try:
            for target in ts.static_order():
                result = target.execute()
                if result:
                    result.print_status()
                    print()
                self.results.append(result)
                result.raise_if_failed()
        except CycleError as e:
            cycle_error = e

        if cycle_error:
            targets = [t.name for t in cycle_error.args[1]]
            raise RunfileFormatError(
                f'Target loop detected: {" -> ".join(targets)}')

        self.stop_containers()
        if self.results:
            return self.results
        else:
            raise TargetNotFoundError(target=target_expr)

    def graph_dependencies(self, target, graph=None):
        if not graph:
            graph = {}
        if target in graph or 'requires' not in target.config:
            return graph

        for subtarget_name in target.config['requires']:
            subtargets = self.find_target(subtarget_name)
            for subtarget in subtargets:
                if target not in graph:
                    graph[target] = set()
                graph[target].add(subtarget)
                dependencies = target.runfile.graph_dependencies(
                    subtarget, graph)
                graph.update(dependencies)

        return graph

    def prepend_include_path(self, include):
        self.header.include_path.insert(0, include)
        for child in self.children:
            self.children[child].prepend_include_path(include)

    def update(self):
        self.children = OrderedDict()
        self.ensure_includes()
        self.name_targets()

    def print_summary(self):
        if not self.results:
            return  # Nothing happened
        if self.results[-1].status != TargetResult.FAILURE:
            status = f'{Fore.GREEN}SUCCESS{Fore.RESET}'
        else:
            status = f'{Fore.RED}FAILURE{Fore.RESET}'
        print(f'{status} in {duration(self.start_time)}')
        print('---')
        for result in self.results:
            result.print_status()

    def container(self):
        return self.targets[None].container

    def stop_containers(self):
        if self.container():
            self.targets[None].stop_container()
        for child in self.children.values():
            child.stop_containers()


class RunfileHeader():
    pattern = (r'^#\s+(?P<name>.+?)$'
               r'(?:\n+>\s+(?P<includes>[^#\n].+?))?$'
               r'(?:\n+(?P<desc>[^\#\n].+?))?$')

    def __init__(self, orig=None, name=None, desc=None, includes=None):
        self.orig = orig
        self.name = name
        self.desc = desc
        self.include_path = []
        if includes:
            pattern = re.compile(r'\[(?P<name>.+?)\]\((?P<path>.+?)\)')
            for match in pattern.finditer(includes):
                self.include_path.append(match.groupdict())

    def __str__(self):
        s = f"# {self.name}"
        if self.include_path:
            links = [f'[{i["name"]}]({i["path"]})' for i in self.include_path]
            s += f"\n\n> Included from {' » '.join(links)}"
        if self.desc:
            s += f"\n\n{self.desc}"
        return s

    def __repr__(self):
        return f'RunfileHeader({self.name},{self.desc},{self.include_path})'

    def __eq__(self, other):
        if not isinstance(other, RunfileHeader):
            return False
        if self.name != other.name:
            return False
        if self.desc != other.desc:
            return False
        return True

    def __hash__(self):
        return hash('|'.join([i['path'] for i in self.include_path]))
