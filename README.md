# Runfile

Runfiles are generic task files defined in Markdown.

For an example, look at [this project’s
Runfile](https://github.com/awkspace/runfile/blob/master/Runfile.md).

## Installation

Install from [PyPI](https://pypi.org/project/runfile/):

```sh
pip install runfile
```

Then add `source <(run --bash-completion)` to your `~/.bashrc` or `~/.zshrc` to
enable tab completion.

## Usage

```sh-session
$ run --help
usage: run [-h] [-f FILENAME] [-u] [--containers] [-l] [--bash-completion] [target]

positional arguments:
  target

optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --file FILENAME
                        Path to Runfile, defaults to Runfile.md
  -u, --update          Update includes
  --containers          Allow steps to run in containers where applicable
  -l, --list-targets    List targets and exit
  --bash-completion     Print bash completion script
```

## Format

Runfiles must include a first-level header at the top of the file.

Each target is defined as a second-level header. Target names can consist of
alphanumeric characters and underscores.

The first paragraph of a target describes the target and will be printed when
`run` is called with no arguments.

Code blocks in targets are executed in the order they are defined. The syntax
highlighting of the code block determines the executable that will run it. For
example, a code block beginning with `python` will execute the code using
`/usr/bin/env python`.

A `yaml` code block represents Runfile or target configuration.

A `dockerfile` code block defines the container that will be used to execute the
given target if `run` is called with `--containers`. To use an existing Docker
image, create a `dockerfile` block that contains only `FROM your_image_name`.

Code blocks directly underneath the top-level header are considered part of a
“global target.” The contents of this global target are executed before any
other target. This is useful for setting variables or performing checks.

## Runfile Configuration

Runfiles are configured by an optional `yaml` block under the top level header.

```yaml
# List of Runfiles to include. Included Runfiles are automatically appended to
# the bottom of the current Runfile. Once a Runfile has been retrieved, it will
# not be updated until run is invoked with --update.
# 
# Each element in the list has a key and a value. The value is the local or
# remote path to the other Runfile; the key is the Runfile alias and can be used
# in other configuration to explicitly reference included targets, e.g.
# my_included_runfile/some_target.
# 
# Use .netrc to fetch Runfiles behind authentication.
includes:
  - example_one: https://example.com/1.md
  - example_two: https://example.com/2.md
```

## Target Configuration

Targets are configured by an optional `yaml` block under their headers.

```yaml
# If the last run was successful, do not rerun this target until this much time
# has passed. Defaults to 0 (no caching). -1 or null caches this target
# indefinitely until invalidated by another target or by a rebuild of a required
# (upstream) target.
expires: 5m

# A list of other targets that should be completed before this target is run.
# Glob matches are supported.
requires:
  - foo
  - bar
  
# A list of other targets that should be immediately expired after a successful
# run of this target. Glob matches are supported. For example, a "clean" target
# may invalidate '*'.
invalidates:
  - baz
```

## Examples

### A “Hello World” Runfile

````markdown
# Hello world

A Runfile that says hello!

## hello

Say hello.

```sh
echo "Hello world!"
```
````

Run it:

```sh-session
$ run
📜 Hello world
A Runfile that says hello!

🎯 Targets
hello: Say hello.

$ run hello
🎯 hello

⏳ Running hello...
Hello world!
✔️ Completed hello. (0.02s)

SUCCESS in 0.04s
---
✔️ Completed hello. (0.02s)
```

### Persistent Values

Use `run_set <key> <value>` to set persistent values. These values are stored
between runs and can be referenced in other code blocks than the one they were
set in. They are also set as environment variables in subsequent code blocks.

Values can be retrieved by `run_get <key>` or by accessing the environment
variable of the same name.

````markdown
# Hello world with two languages

A Runfile that says hello using two languages!

## write_message

Writes a message to the Runfile cache using shell.

```sh
run_set "message" "Hello world!"
```

## print_message

Prints a stored message from the Runfile cache using Python.

```python
import os
print(os.environ["message"])
```

## delete_message

Deletes the stored message using shell.

```sh
run_del "message"
```
````

Run it:

```sh-session
$ run write_message 
🎯 write_message

⏳ Running write_message...
✔️ Completed write_message. (0.24s)

SUCCESS in 0.27s
---
✔️ Completed write_message. (0.24s)

$ run print_message 
🎯 print_message

⏳ Running print_message...
Hello world!
✔️ Completed print_message. (0.03s)

SUCCESS in 0.06s
---
✔️ Completed print_message. (0.03s)
```

This works, but now there’s a problem: running `print_message` before
`write_message` results in an error.

```sh-session
$ run delete_message 
🎯 delete_message

⏳ Running delete_message...
1
✔️ Completed delete_message. (0.25s)

SUCCESS in 0.28s
---
✔️ Completed delete_message. (0.25s)

$ run print_message 
🎯 print_message

⏳ Running print_message...
Traceback (most recent call last):
  File "/tmp/tmp5d8zepzl/run", line 2, in <module>
    print(os.environ["message"])
  File "os.py", line 679, in __getitem__
    raise KeyError(key) from None
KeyError: 'message'
❌ Failed print_message. (0.05s)

FAILURE in 0.05s
---
❌ Failed print_message. (0.05s)
```

### Dependencies

To fix this, use the `requires` directive in the `print_message` target
configuration.

````markdown
# Hello world with dependencies

A Runfile that says hello, but less broken this time.

## write_message

Writes a message to the Runfile cache using shell.

```sh
run_set "message" "Hello world!"
```

## print_message

Prints a stored message from the Runfile cache using Python.

```yaml
requires:
  - write_message
```

```python
import os
print(os.environ["message"])
```

## delete_message

Deletes the stored message using shell.

```sh
run_del "message"
```
````

Now the message will be written every time `print_message` is run.

```sh-session
$ run delete_message 
🎯 delete_message

⏳ Running delete_message...
1
✔️ Completed delete_message. (0.26s)

SUCCESS in 0.29s
---
✔️ Completed delete_message. (0.26s)

$ run print_message 
🎯 print_message

⏳ Running write_message...
✔️ Completed write_message. (0.26s)

⏳ Running print_message...
Hello world!
✔️ Completed print_message. (0.04s)

SUCCESS in 0.37s
---
✔️ Completed write_message. (0.26s)
✔️ Completed print_message. (0.04s)
```

### Caching

However, constantly rerunning a dependency with a cacheable value is not always
an ideal situation. Some targets may take a while to run.

We can simulate this by adding a `sleep` command to `write_message`, then
configuring its `expires` directive such that it runs at most once per day.

````markdown
# Hello world with dependencies and caching

A Runfile that says hello, but it takes a while.

## write_message

```yaml
expires: 24h
```

Writes a message to the Runfile cache using shell.

```sh
sleep 5  # Simulate a long operation
run_set "message" "Hello world!"
```

## print_message

Prints a stored message from the Runfile cache using Python.

```yaml
requires:
  - write_message
```

```python
import os
print(os.environ["message"])
```

## delete_message

Deletes the stored message using shell.

```sh
run_del "message"
```
````

Executing `run print_message` takes a while the first time:

```sh-session
$ run print_message 
🎯 print_message

⏳ Running write_message...
✔️ Completed write_message. (5.25s)

⏳ Running print_message...
Hello world!
✔️ Completed print_message. (0.03s)

SUCCESS in 5.34s
---
✔️ Completed write_message. (5.25s)
✔️ Completed print_message. (0.03s)
```

But running it again will skip the `write_message` target:

``` sh-session
$ run print_message
🎯 print_message

💾 Used cache for write_message.

⏳ Running print_message...
Hello world!
✔️ Completed print_message. (0.07s)

SUCCESS in 0.13s
---
💾 Used cache for write_message.
✔️ Completed print_message. (0.07s)
```

This saves time, but it also introduces a new problem. Running `delete_message`
will delete the message, but the Runfile doesn’t know that `write_message` needs
to be rerun before the next `print_message`!

### Cache Invalidation

The `invalidates` directive can be used to indicate that running a specific
target will result in the cached values of other targets being invalid.

````markdown
# Hello world with dependencies and caching

A Runfile that says hello, but it takes a while.

## write_message

```yaml
expires: 24h
```

Writes a message to the Runfile cache using shell.

```sh
sleep 5  # Simulate a long operation
run_set "message" "Hello world!"
```

## print_message

Prints a stored message from the Runfile cache using Python.

```yaml
requires:
  - write_message
```

```python
import os
print(os.environ["message"])
```

## delete_message

Deletes the stored message using shell.

```yaml
invalidates:
  - write_message
```

```sh
run_del "message"
```
````

Now running `delete_message` invalidates the `write_message` cache.

```sh-session
$ run delete_message
🎯 delete_message

⏳ Running delete_message...
1
✔️ Completed delete_message. (0.28s)

SUCCESS in 0.31s
---
✔️ Completed delete_message. (0.28s)

$ run print_message 
🎯 print_message

⏳ Running write_message...
✔️ Completed write_message. (5.24s)

⏳ Running print_message...
Hello world!
✔️ Completed print_message. (0.06s)

SUCCESS in 5.37s
---
✔️ Completed write_message. (5.24s)
✔️ Completed print_message. (0.06s)
```

Changing the content of a code block will also invalidate the cache of a target.
And, like `make`, a target with a dependency run more recently than the target
itself will invalidate that target’s cache.

## Running Targets Inside Containers

Add a [Dockerfile](https://docs.docker.com/engine/reference/builder/) block at
the top of a target and Runfile will build a container accordingly, then mount
the current directory into the Docker container before running commands.

By default, Runfiles will not execute these code blocks. Most of the time,
Runfiles are expected to be run on a user’s system, with dependencies manually
installed. However, containers are useful for executing Runfiles on CI systems
where dependencies are not controlled by the user.

To execute a Runfile target in containerized mode, use the `--containers` flag.

Container images will be cached until the content of a `dockerfile` block
changes.

## Including Other Runfiles

Other Runfiles can be included via an `includes` directive in the Runfile
configuration block.

Included Runfiles will automatically append themselves to the main Runfile. This
promotes consolidation of common tasks to shared files without sacrificing the
portability and stability of any given Runfile.

To refresh included Runfiles, execute `run` with the `--update` flag.

## Configuration Options

If you hate fun, set `RUNFILE_NO_EMOJI=1` to disable icons from the output.
