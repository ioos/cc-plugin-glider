from __future__ import with_statement
import versioneer
from setuptools import setup, find_packages


def readme():
    with open('README.md') as f:
        return f.read()


reqs = [line.strip() for line in open('requirements.txt')]


setup(
    name="cc-plugin-glider",
    version=versioneer.get_version(),
    description="Compliance Checker Glider DAC plugin",
    long_description=readme(),
    long_description_content_type="text/markdown",
    license='Apache License 2.0',
    author="Robert Fratantonio",
    author_email="robert.fratantonio@rpsgroup.com",
    url="https://github.com/ioos/compliance-checker",
    packages=find_packages(),
    install_requires=reqs,
    tests_require=['pytest'],
    package_data={
        'cc_plugin_glider': ['data/*.csv']
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering'
    ],
    entry_points={
        'compliance_checker.suites': ['gliderdac = cc_plugin_glider.glider_dac:GliderCheck']
    },
    cmdclass=versioneer.get_cmdclass(),
)
