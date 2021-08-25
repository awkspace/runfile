#!/usr/bin/env python3

import pytest
from runfile.exceptions import RunfileFormatError
from runfile.target import Target


@pytest.mark.parametrize("name,valid", [
    ['foo', True],
    ['foo bar', False],
    ['foo:bar', True],
    ['FooBar', True],
    ['foo-bar', False],
    [':foo', False],
    ['bar_', False]
])
def test_validate(name, valid):
    if valid:
        Target(name=name)
    else:
        with pytest.raises(RunfileFormatError) as execinfo:
            Target(name=name)
