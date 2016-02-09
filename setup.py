from __future__ import with_statement

import os
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


def extract_version(module='cc_plugin_glider'):
    version = None
    fdir = os.path.dirname(__file__)
    fnme = os.path.join(fdir, module, '__init__.py')
    with open(fnme) as fd:
        for line in fd:
            if (line.startswith('__version__')):
                _, version = line.split('=')
                # Remove quotation characters.
                version = version.strip()[1:-1]
                break
    return version


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        # Import here, cause outside the eggs aren't loaded.
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


def readme():
    with open('README.md') as f:
        return f.read()

reqs = [line.strip() for line in open('requirements.txt')]

setup(name="cc-plugin-glider",
      version=extract_version(),
      description="Compliance Checker Glider DAC plugin",
      long_description=readme(),
      license='Apache License 2.0',
      author="Luke Campbell",
      author_email="lcampbell@asascience.com",
      url="https://github.com/ioos/compliance-checker",
      packages=find_packages(),
      install_requires=reqs,
      tests_require=['pytest'],
      cmdclass=dict(test=PyTest),
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering'],
      entry_points={'compliance_checker.suites':
                    ['gliderdac = cc_plugin_glider.glider_dac:GliderCheck']})
