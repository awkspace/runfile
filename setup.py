#!/usr/bin/env python3

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.readlines()

with open('dev_requirements.txt') as dev_requirements_file:
    dev_requirements = dev_requirements_file.readlines()

try:
    import graphlib  # noqa: F401
except ImportError:
    requirements.append('graphlib_backport')

setup(
    name='runfile',
    author='awk',
    author_email='awk@awk.space',
    version='1.0.6',
    description='A generic task-based automation format.',
    long_description=readme,
    long_description_content_type='text/markdown',
    license='MIT',
    url='https://github.com/awkspace/runfile',
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements
    },
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'run = runfile.cli:main',
            'run_get = runfile.vars:get',
            'run_set = runfile.vars:set',
            'run_del = runfile.vars:delete'
        ]
    }
)
