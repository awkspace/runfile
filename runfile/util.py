#!/usr/bin/env python3

import humanize
import os
import re
import time
from colorama import Fore, Style
from datetime import timedelta


def msg(message, kind=None, suffix=None):
    out = ''
    style_applied = False

    if not os.environ.get('RUNFILE_NO_EMOJI') and kind["icon"]:
        out += f'{kind["icon"]} '
    elif not os.environ.get('RUNFILE_NO_COLOR') and kind["style"]:
        out += f'{kind["style"]}'
        style_applied = True

    out += message
    if style_applied:
        out += f'{Style.RESET_ALL}'

    if suffix:
        out += f' {suffix}'

    print(out)


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
    if s is None:
        return None
    seconds = 0
    patterns = {
        r'(-?[0-9]+)m': 60,
        r'(-?[0-9]+)h': 60 * 60,
        r'(-?[0-9]+)d': 60 * 60 * 24,
        r'(-?[0-9]+)w': 60 * 60 * 24 * 7,
        r'(-?[0-9]+)s?': 1
    }
    for pattern, factor in patterns.items():
        match = re.search(pattern, s)
        if match:
            s = re.sub(pattern, '', s)
            seconds += int(match.group(1)) * factor
    return seconds


def to_plaintext(text):
    if not text:
        return None

    text = re.sub(r'\n+', " ", text)
    text = re.sub(r' +', " ", text)
    for char in list('_*`'):
        regex = re.compile(f'\\{char}(.+?)\\{char}')
        text = re.sub(regex, r'\1', text)

    return text


class MsgType():
    FILE = {
        'icon': '📜',
        'style': None
    }
    TARGET = {
        'icon': '🎯',
        'style': '\033[4m'
    }
    WORKING = {
        'icon': '⏳',
        'style': Fore.BLUE
    }
    CONTAINER = {
        'icon': '📦',
        'style': Fore.BLUE
    }
    SUCCESS = {
        'icon': '✔',
        'style': Fore.GREEN
    }
    FAILURE = {
        'icon': '❌',
        'style': Fore.RED
    }
    NEUTRAL = {
        'icon': None,
        'style': Style.DIM
    }
    CACHE = {
        'icon': '💾',
        'style': Style.DIM
    }


class Error():
    DUPLICATE_HEADER = 'Only one top-level header is permitted per Runfile.'
    NO_HEADER = 'Missing Runfile header.'
    INCLUDE_MULTIPLE_KEYS = 'Includes must contain one key.'
    DUPLICATE_INCLUDE = 'Duplicate include alias: {}'
    TARGET_LOOP = 'Target loop detected: {}'
    DUPLICATE_TARGET = 'Duplicate target name: {}'
