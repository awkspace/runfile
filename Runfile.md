# Runfile

Installs dependencies to a local `lib` directory to avoid conflicting with a
global install of `run`.

Invoke `lib/run` for the development version.

```python
import os
lib_path = './lib'
paths = os.environ.get('PYTHONPATH', '').split(':')
paths = [path for path in paths if path]
if lib_path not in paths:
    paths.append(lib_path)
os.system(f'run_set "PYTHONPATH" {":".join(paths)}')
```

## test

Test package.

```yaml
requires:
  - devinstall
```

```sh
python3 -m pytest --ignore lib --cov=runfile --cov-report term
```

## test:cov

Test package and open up a coverage report.

```yaml
requires:
  - devinstall
```

```sh
covdir="$(mktemp -d)"
python3 -m pytest --ignore lib --cov=runfile --cov-report "html:$covdir"
sensible-browser "file://$covdir/index.html"
run_set "covfile" "$covdir/index.html"
```

## lint

Lint package.

```yaml
requires:
  - devinstall
```

```sh
flake8 --exclude lib
```

## install

Install package from source.

```yaml
expires: null
```

```sh
pip install .
```

## devinstall

Install package from source including development dependenices.

```yaml
expires: null
```

```sh
pip install -e .[dev] -U --target lib
```

## build

Create source distribution for publishing.

```yaml
requires:
  - lint
```

```sh
rm -f dist/*
python setup.py sdist
```

## publish:test

Upload package to test.pypi.org.

```yaml
requires:
  - devinstall
  - build
```
```sh
lib/bin/twine upload --repository testpypi dist/*
```

## publish:live

Upload package to pypi.org.

```yaml
requires:
  - devinstall
  - build
```
```sh
lib/bin/twine upload --repository pypi dist/*
```

## clean

```yaml
invalidates:
  - build
```

## clean:all

```yaml
invalidates:
  - install
  - devinstall
```

```sh
rm -rf ./lib
```
