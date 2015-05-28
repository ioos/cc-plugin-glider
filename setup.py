from __future__ import with_statement
import sys

from setuptools import setup, find_packages

from cc_plugin_glider import __version__

def readme():
    with open('README.md') as f:
        return f.read()

reqs = [line.strip() for line in open('requirements.txt')]

setup(name                 = "cc-plugin-glider",
    version              = __version__,
    description          = "Compliance Checker Glider DAC plugin",
    long_description     = readme(),
    license              = 'Apache License 2.0',
    author               = "Luke Campbell",
    author_email         = "lcampbell@asascience.com",
    url                  = "https://github.com/ioos/compliance-checker",
    packages             = find_packages(),
    install_requires     = reqs,
    classifiers          = [
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python',
            'Topic :: Scientific/Engineering',
        ],
    entry_points         = {
        'compliance_checker.suites': [
            'gliderdac = cc_plugin_glider.glider_dac:GliderCheck',
        ]
    }
)

