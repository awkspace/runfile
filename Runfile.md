# Runfile

Installs dependencies to a local `lib` directory to avoid conflicting with a
global install of`run`.

Invoke `lib/run` for the development version.

```python
import os
lib_path = './lib'
path = os.environ.get('PYTHONPATH', '').split(':')
if lib_path not in path:
    path.append(lib_path)
os.system(f'run_set "PYTHONPATH" {":".join(path)}')
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

## test_cov

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

```yaml
expires: null
```

Create source distribution.

```sh
rm -f dist/*
python setup.py sdist
```

## upload_test_pypi

Upload package to test.pypi.org.

```yaml
requires:
  - devinstall
  - build
```
```sh
lib/bin/twine upload --repository testpypi dist/*
```

## upload_live_pypi

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
  - '*'
```

```sh
rm -rf ./lib
```
