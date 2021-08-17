# Runfile

```python
import os
lib_path = './lib'
path = os.environ.get('PYTHONPATH', '').split(':')
if lib_path not in path:
    path.append(lib_path)
os.system(f'run_set "PYTHONPATH" {":".join(path)}')
```

## test

```yaml
requires:
  - devinstall
```

```sh
python3 -m pytest --ignore lib
```

## lint

```yaml
requires:
  - devinstall
```

```sh
flake8 --exclude lib
```

## install

```yaml
expires: null
```

```sh
pip install . -U --target lib
```

## devinstall

```yaml
expires: null
```

```sh
pip install -e .[dev] -U --target lib
```

## clean

```yaml
invalidates:
  - '*'
```

```sh
rm -rf ./lib
```
