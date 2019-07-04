# -*- coding: utf-8 -*-


"""setup.py: setuptools control."""


import sys
import re
from setuptools import setup
from setuptools.command.test import test as TestCommand
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), 'r') as f:
    long_description = f.read()

version = "1.0.2"


class PyTest(TestCommand):

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

setup(
    name="cfn-resource-provider",
    packages=["cfn_resource_provider"],
    entry_points={},
    version=version,
    description="A base class for AWS CloudFormation Custom Resource Providers.",
    long_description=long_description,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=['requests',  'future', 'jsonschema', 'requests[security]'],
    cmdclass={'test': PyTest},
    tests_require=['pytest'],
    author="Mark van Holsteijn",
    author_email="markvanholsteijn@binx.io",
    url="https://github.com/binxio/cfn-resource-provider",
)
