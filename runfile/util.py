#!/usr/bin/env python3

import humanize
import re
import time
from datetime import timedelta


def humanize_abbreviated(s):
    abbreviations = {
        r' milliseconds?': 'ms',
        r' seconds?': 's',
        r' minutes?': 'm',
        r' hours?': 'h',
        r' days?': 'd'
    }
    for search, replace in abbreviations.items():
        s = re.sub(search, replace, s)
    return s


def duration(time1, time2=None):
    if not time2:
        time2 = time.time()
    seconds = time2 - time1
    delta = timedelta(seconds=seconds)
    humanized = humanize.precisedelta(delta, minimum_unit='seconds')
    return humanize_abbreviated(humanized)


def human_time_to_seconds(s):
    seconds = 0
    patterns = {
        r'([0-9]+)m': 60,
        r'([0-9]+)h': 60 * 60,
        r'([0-9]+)d': 60 * 60 * 24,
        r'([0-9]+)w': 60 * 60 * 24 * 7,
        r'([0-9]+)s': 1
    }
    for pattern, factor in patterns.items():
        match = re.search(pattern, s)
        if match:
            seconds += int(match.group(1)) * factor
    return seconds
