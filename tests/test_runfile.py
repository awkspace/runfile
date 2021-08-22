#!/usr/bin/env python3

import pytest
import yaml
from textwrap import dedent
from runfile import Runfile, RunfileHeader
from runfile.target import Target
from runfile.code_block import CodeBlock
from runfile.exceptions import RunfileNotFoundError, RunfileFormatError
from runfile.util import Error

runfile_examples = {
    'basic': {
        'content': """\
        # An example Runfile

        ## Target_1

        ```sh
        echo "Hello world"
        ```

        ## Target_2

        ```js
        console.log("Hello world");
        ```
        """,
        'tokenized': [
            RunfileHeader('', "An example Runfile", None, None),
            Target('', "Target_1", None),
            CodeBlock('', "sh", 'echo "Hello world"'),
            Target('', "Target_2", None),
            CodeBlock('', "js", 'console.log("Hello world");')
        ]
    },
    'with_descriptions': {
        'content': """\
        # An example Runfile

        A description of this Runfile.
        This should be included in the description!

        ## Target_1

        A description for Target_1.

        This shouldn't appear in the description!

        ```sh
        echo "Hello world"
        ```

        ## Target_2

        A description for Target_2.

        ```js
        console.log("Hello world");
        ```
        """,
        'tokenized': [
            RunfileHeader(
                '',
                "An example Runfile",
                "A description of this Runfile. "
                "This should be included in the description!",
                None),
            Target('', "Target_1", "A description for Target_1."),
            CodeBlock('', "sh", 'echo "Hello world"'),
            Target('', "Target_2", "A description for Target_2."),
            CodeBlock('', "js", 'console.log("Hello world");')
        ]
    },
    'multi_block': {
        'content': """\
        # An example Runfile

        ## Target_1

        ```sh
        echo "Hello world from first code block"
        ```

        ```sh
        echo "Hello world from second code block"
        ```

        ## Target_2

        ```yaml
        foo: bar
        biz: baz
        ```

        ```js
        console.log("Hello world");
        ```
        """,
        'tokenized': [
            RunfileHeader('', "An example Runfile", None, None),
            Target('', "Target_1", None),
            CodeBlock('', "sh", 'echo "Hello world from first code block"'),
            CodeBlock('', "sh", 'echo "Hello world from second code block"'),
            Target('', "Target_2", None),
            CodeBlock('', "yaml", "foo: bar\nbiz: baz"),
            CodeBlock('', "js", 'console.log("Hello world");')
        ]
    },
    'comments_in_block': {
        'content': """\
        # An example Runfile

        ## Target

        ```sh
        echo "Hello world"
        # This is a comment
        ## It is not markdown
        ### Don't parse it as markdown!
        ```
        """,
        'tokenized': [
            RunfileHeader('', "An example Runfile", None, None),
            Target('', "Target", None),
            CodeBlock(
                '',
                "sh",
                dedent("""\
                echo "Hello world"
                # This is a comment
                ## It is not markdown
                ### Don't parse it as markdown!""")
            )
        ]
    },
    'with_child': {
        'content': """\
        # An example Runfile

        ## Target_1

        ```sh
        echo "Hello world"
        ```

        ## Target_2
        ```js
        console.log("Hello world");
        ```

        # An example included Runfile

        > [child](https://example.com)

        ## Target_3

        ```python
        print("Hello world")
        ```
        """,
        'tokenized': [
            RunfileHeader('', "An example Runfile", None, None),
            Target('', "Target_1", None),
            CodeBlock('', "sh", 'echo "Hello world"'),
            Target('', "Target_2", None),
            CodeBlock('', "js", 'console.log("Hello world");')
        ],
        'child_tokenized': [
            RunfileHeader(
                '',
                "An example included Runfile",
                None,
                '[child](https://example.com)'
            ),
            Target('', "Target_3", None),
            CodeBlock('', "python", 'print("Hello world")')
        ]
    },
}


def test_read_file(mocker):
    rf = Runfile('MyRunfile.md')
    open_ = mocker.patch('builtins.open', mocker.mock_open(read_data='data'))

    ret = rf.read_file()

    assert ret == 'data'
    open_.assert_called_once_with('MyRunfile.md', 'r')
    open_.return_value.read.assert_called_once_with()


def test_write_file(mocker):
    rf = Runfile('MyRunfile.md')
    open_ = mocker.patch('builtins.open', mocker.mock_open())

    rf.write_file('data')

    open_.assert_called_once_with('MyRunfile.md', 'w')
    open_.return_value.write.assert_called_once_with('data')


def test_save(mocker):
    rf = Runfile('MyRunfile.md')
    rf_str = mocker.patch.object(Runfile, '__str__', return_value='data')
    rf_write = mocker.patch.object(Runfile, 'write_file')

    rf.save()

    rf_str.assert_called_once_with()
    rf_write.assert_called_once_with(rf_str.return_value)


def test_load(mocker):
    rf = Runfile('MyRunfile.md')
    rf_tokenize = mocker.patch.object(Runfile, 'tokenize')

    rf.load()

    rf_tokenize.assert_called_once_with()


def test_content_local_file(mocker):
    rf = Runfile('MyRunfile.md')
    rf_read = mocker.patch.object(Runfile, 'read_file')
    file_exists = mocker.patch('os.path.exists', return_value=True)

    ret = rf.content()

    assert ret == rf_read.return_value
    file_exists.assert_called_once_with('MyRunfile.md')
    rf_read.assert_called_once_with()


def test_content_remote_file(mocker):
    rf = Runfile('https://example.com/MyRunfile.md')
    rf_read = mocker.patch.object(Runfile, 'read_file')
    file_exists = mocker.patch('os.path.exists', return_value=False)
    rq_response = mocker.MagicMock()
    rq_response.status_code = 200
    rq_get = mocker.patch('requests.get', return_value=rq_response)

    ret = rf.content()

    assert ret == rq_response.text
    file_exists.assert_called_once_with('https://example.com/MyRunfile.md')
    rf_read.assert_not_called()
    rq_get.assert_called_once_with('https://example.com/MyRunfile.md')


def test_content_local_file_not_found(mocker):
    rf = Runfile('MyRunfile.md')
    rf_read = mocker.patch.object(Runfile, 'read_file')
    file_exists = mocker.patch('os.path.exists', return_value=False)

    with pytest.raises(RunfileNotFoundError) as excinfo:
        rf.content()

    assert excinfo.value.path == 'MyRunfile.md'
    file_exists.assert_called_once_with('MyRunfile.md')
    rf_read.assert_not_called()


def test_content_remote_file_not_found(mocker):
    rf = Runfile('https://example.com/MyRunfile.md')
    rf_read = mocker.patch.object(Runfile, 'read_file')
    file_exists = mocker.patch('os.path.exists', return_value=False)
    rq_response = mocker.MagicMock()
    rq_response.status_code = 404
    rq_get = mocker.patch('requests.get', return_value=rq_response)

    with pytest.raises(RunfileNotFoundError) as excinfo:
        rf.content()

    assert excinfo.value.path == 'https://example.com/MyRunfile.md'
    file_exists.assert_called_once_with('https://example.com/MyRunfile.md')
    rf_read.assert_not_called()
    rq_get.assert_called_once_with('https://example.com/MyRunfile.md')


@pytest.mark.parametrize("tokens", [
    ["foo", "bar"],
    ["foo", "bar", "\n\n\n\n"],
    ["foo", "bar\n"]
])
def test_str(mocker, tokens):
    rf = Runfile('MyRunfile.md')
    child_rf = mocker.MagicMock()
    rf.children = {'child': child_rf}
    child_rf.__str__ .return_value = "baz"
    rf.tokens = tokens

    ret = str(rf)

    assert ret == "foobar\n\nbaz\n"
    child_rf.__str__.assert_called_once_with()


def test_hash(mocker):
    rf = Runfile('MyRunfile.md')
    mocker.patch.object(rf, 'header')

    ret = hash(rf)

    assert ret == rf.header.__hash__.return_value


@pytest.mark.parametrize("key", runfile_examples.keys())
def test_tokenize(mocker, key):
    rf_content = mocker.patch.object(Runfile, 'content')
    rf_content.return_value = dedent(runfile_examples[key]['content'])
    rf_ensure_includes = mocker.patch.object(Runfile, 'ensure_includes')
    rf_name_targets = mocker.patch.object(Runfile, 'name_targets')

    rf = Runfile('some_file.md')
    rf.tokenize()

    tokens_only = [t for t in rf.tokens if not isinstance(t, str)]
    assert tokens_only == runfile_examples[key]['tokenized']
    if "child" in runfile_examples[key]:
        child_tokens_only = [
            t for t in rf.child['child']
            if not isinstance(t, str)
        ]
        assert child_tokens_only == runfile_examples[key]['child_tokenized']
    rf_ensure_includes.assert_called_once_with()
    rf_name_targets.assert_called_once_with()


def test_tokenize_double_header(mocker):
    rf_content = mocker.patch.object(Runfile, 'content')
    rf_content.return_value = dedent("""\
    # Some Runfile Header

    A runfile with two heads!

    # Another Runfile Header

    This is illegal you know.
    """)

    rf = Runfile('some_file.md')
    with pytest.raises(RunfileFormatError) as excinfo:
        rf.tokenize()

    assert str(excinfo.value) == Error.DUPLICATE_HEADER


def test_tokenize_missing_header(mocker):
    rf_content = mocker.patch.object(Runfile, 'content')
    rf_content.return_value = dedent("""\
    ## target_definition_before_header
    """)

    rf = Runfile('some_file.md')
    with pytest.raises(RunfileFormatError) as excinfo:
        rf.tokenize()

    assert str(excinfo.value) == Error.NO_HEADER


def test_parse_duplicate_target():
    rf = Runfile('some_file.md')
    rf.tokens = [
        Target('', 'Target_1', None),
        Target('', 'Target_2', None),
        Target('', 'Target_2', None)
    ]

    with pytest.raises(RunfileFormatError) as excinfo:
        rf.parse()

    assert str(excinfo.value) == Error.DUPLICATE_TARGET.format("Target_2")


def test_parse_special_blocks(mocker):
    rf = Runfile('some_file.md')
    sh_block = CodeBlock('', 'sh', 'some shell code')
    rf.tokens = [
        Target('', 'Target_1', None),
        CodeBlock('', 'yaml', 'yaml config'),
        CodeBlock('', 'dockerfile', 'dockerfile definition'),
        sh_block
    ]
    yaml_load = mocker.patch('yaml.load')

    rf.parse()

    assert rf.targets['Target_1'].config == yaml_load.return_value
    assert rf.targets['Target_1'].dockerfile == 'dockerfile definition'
    assert rf.targets['Target_1'].blocks == [sh_block]
    yaml_load.assert_called_once_with('yaml config', Loader=yaml.SafeLoader)


def test_loading_includes(mocker):
    rf = Runfile('some_file.md')
    rf.targets = {None: Target(None)}
    rf.targets[None].config = {
        'includes': [
            {'include_1': 'https://example.com/Include1.md'},
            {'include_2': 'https://example.com/Include2.md'}
        ]
    }

    ret = rf.includes()

    assert ret == {
        'include_1': 'https://example.com/Include1.md',
        'include_2': 'https://example.com/Include2.md'
    }


def test_include_too_many_maps(mocker):
    rf = Runfile('some_file.md')
    rf.targets = {None: Target(None)}
    rf.targets[None].config = {
        'includes': [
            {
                'include_1': 'https://example.com/Include1.md',
                'include_2': 'https://example.com/Include2.md'
            }
        ]
    }

    with pytest.raises(RunfileFormatError) as excinfo:
        rf.includes()

    assert str(excinfo.value) == Error.INCLUDE_MULTIPLE_KEYS


def test_include_duplicate_key(mocker):
    rf = Runfile('some_file.md')
    rf.targets = {None: Target(None)}
    rf.targets[None].config = {
        'includes': [
            {'include_1': 'https://example.com/Include1.md'},
            {'include_1': 'https://example.com/Include2.md'}
        ]
    }

    with pytest.raises(RunfileFormatError) as excinfo:
        rf.includes()

    assert str(excinfo.value) == Error.DUPLICATE_INCLUDE.format('include_1')
