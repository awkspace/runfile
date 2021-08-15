#!/usr/bin/env python3

import sys
from runfile.cache import RunfileCache


def get():
    if len(sys.argv) < 2:
        print("Usage: run_get <key>", file=sys.stderr)
        sys.exit(2)

    cache = RunfileCache()
    value = cache['vars'][sys.argv[1]]
    if value:
        print(value, end='')
    else:
        sys.exit(1)


def set():
    if len(sys.argv) < 3:
        print("Usage: run_set <key> <value>", file=sys.stderr)
        sys.exit(2)

    cache = RunfileCache()
    cache['vars'][sys.argv[1]] = ' '.join(sys.argv[2:])


def delete():
    if len(sys.argv) < 2:
        print("Usage: run_del <key1> [key2] [key3]...", file=sys.stderr)
        sys.exit(2)

    cache = RunfileCache()
    count = 0
    for key in sys.argv[1:]:
        if cache['vars'][key]:
            del cache['vars'][key]
            count += 1

    print(count, end='')
