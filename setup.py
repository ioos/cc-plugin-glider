from __future__ import with_statement

import os

from setuptools import setup, find_packages


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


def readme():
    with open('README.md') as f:
        return f.read()


reqs = [line.strip() for line in open('requirements.txt')]


setup(name="cc-plugin-glider",
      version=extract_version(),
      description="Compliance Checker Glider DAC plugin",
      long_description=readme(),
      license='Apache License 2.0',
      author="Robert Fratantonio",
      author_email="robert.fratantonio@rpsgroup.com",
      url="https://github.com/ioos/compliance-checker",
      packages=find_packages(),
      install_requires=reqs,
      tests_require=['pytest'],
      package_data={'cc_plugin_glider': ['data/*.csv']},
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
