#!/usr/bin/env python3

import os
import sys
from argparse import ArgumentParser
from runfile import Runfile
from runfile.exceptions import TargetNotFoundError, TargetExecutionError, \
    RunfileFormatError, RunfileNotFoundError

# TODO: Tab completion of targets, flags
# TODO: --list to list targets
# TODO: --describe to list targets & descriptions


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-f', '--file', dest='filename', default='Runfile.md',
        help='Path to Runfile, defaults to Runfile.md')
    parser.add_argument(
        '-u', '--update', dest='update', action='store_true',
        help='Update includes')
    parser.add_argument('target', nargs='?')
    parser.add_argument(
        '--containers', dest='containers', action='store_true',
        help='Allow steps to run in containers where applicable')
    parser.add_argument(
        '-l', '--list-targets', dest='list_targets', action='store_true',
        help='List targets and exit')
    parser.add_argument(
        '--bash-completion', dest='bash_completion', action='store_true',
        help='Print bash completion script')
    args = parser.parse_args()

    if args.bash_completion:
        completion_file = os.path.join(
            os.path.dirname(__file__), 'resources', 'completion.bash')
        with open(completion_file, 'r') as f:
            print(f.read())
        return

    rf = Runfile(args.filename, root=True)
    try:
        rf.load()
        if args.update:
            rf.update()
        rf.save()
    except RunfileFormatError as e:
        print(f'RunfileFormatError: {str(e)}', file=sys.stderr)
        sys.exit(1)
    except RunfileNotFoundError as e:
        print(f'Runfile not found: {e.path}', file=sys.stderr)
        sys.exit(1)

    if args.list_targets:
        for target in rf.list_targets():
            if target.name:
                print(target.unique_name)
        return

    if not args.target:
        has_targets = False
        for target in rf.list_targets():
            has_targets = True
            if target.name and target.desc:
                print(f'{target.unique_name}: {target.desc}')
            elif target.name:
                print(target.unique_name)
        if not has_targets:
            print('No targets found.', file=sys.stderr)
        return

    if args.containers:
        rf.use_containers = True

    try:
        rf.execute_target(args.target)
    except TargetNotFoundError as e:
        print(f"Target not found: {e.target}", file=sys.stderr)
        sys.exit(1)
    except TargetExecutionError as e:
        sys.exit(e.exit_code)
    finally:
        rf.print_summary()
