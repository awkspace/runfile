#!/usr/bin/env python3

import pytest
from textwrap import dedent
from runfile import Runfile, RunfileHeader
from runfile.target import Target
from runfile.code_block import CodeBlock

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
                "A description of this Runfile.",
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


@pytest.mark.parametrize("key", runfile_examples.keys())
def test_tokenize(mocker, key):
    content = mocker.patch.object(Runfile, 'content')
    content.return_value = dedent(runfile_examples[key]['content'])

    runfile = Runfile('some_file.md')
    runfile.tokenize()

    tokens_only = [t for t in runfile.tokens if not isinstance(t, str)]
    assert tokens_only == runfile_examples[key]['tokenized']
