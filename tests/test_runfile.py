#!/usr/bin/env python3

import pytest
from textwrap import dedent
from runfile import Runfile, RunfileHeader
from runfile.target import Target
from runfile.code_block import CodeBlock
from runfile.exceptions import RunfileNotFoundError

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
    }
}


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
    content = mocker.patch.object(Runfile, 'content')
    content.return_value = dedent(runfile_examples[key]['content'])

    runfile = Runfile('some_file.md')
    runfile.tokenize()

    tokens_only = [t for t in runfile.tokens if not isinstance(t, str)]
    assert tokens_only == runfile_examples[key]['tokenized']


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
