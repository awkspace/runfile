#!/usr/bin/env python3

import sys
from argparse import ArgumentParser
from runfile import Runfile
from runfile.exceptions import TargetNotFoundError, \
    TargetExecutionError, RunfileFormatError

# TODO: Tab completion of targets, flags
# TODO: --list to list targets
# TODO: --describe to list targets & descriptions


def main():
    parser = ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('-f', '--file', dest='filename', default='Runfile.md')
    parser.add_argument('-u', '--update', dest='update', action='store_true')
    args = parser.parse_args()

    rf = Runfile(args.filename)
    try:
        rf.load()
        if args.update:
            rf.update()
        rf.save()
    except RunfileFormatError as e:
        print(f'RunfileFormatError: {str(e)}')
        sys.exit(1)

    try:
        rf.execute_target(args.target)
    except TargetNotFoundError as e:
        print(f"Target not found: {e.target}")
        sys.exit(1)
    except TargetExecutionError as e:
        sys.exit(e.exit_code)
    finally:
        rf.print_summary()
