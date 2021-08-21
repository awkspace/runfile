#!/usr/bin/env python3

import pytest

from runfile.util import to_plaintext


@pytest.mark.parametrize(
    ["in_", "out"],
    [
        ["A *bold* assumption.", "A bold assumption."],
        ["Hello\n\n\n world!", "Hello world!"],
        ["A `grave error.", "A `grave error."],
        [
            "A  _ridiculous_ amount of emphasis;   simply _ridiculous_.",
            "A ridiculous amount of emphasis; simply ridiculous."
         ]
    ]
)
def test_to_plaintext(in_, out):
    assert to_plaintext(in_) == out
