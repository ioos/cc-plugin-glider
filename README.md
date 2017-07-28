# GliderDAC Compliance Checker Plugin

[![Build Status](https://travis-ci.org/ioos/cc-plugin-glider.svg?branch=master)](https://travis-ci.org/ioos/cc-plugin-glider)

This [ioos/compliance-checker](https://github.com/ioos/compliance-checker) plugin supports the following sources and standards:

| Standard                                                                                             | Checker Name |
| ---------------------------------------------------------------------------------------------------- | ------------ |
| [Glider DAC](https://github.com/ioos/ioosngdac/wiki/NGDAC-NetCDF-File-Format-Version-2)              |  gliderdac   |


## Installation

### Conda

```shell
$ conda install -c conda-forge cc-plugin-glider
```

### Pip

```shell
$ pip install cc-plugin-glider
```

See the [ioos/compliance-checker](https://github.com/ioos/compliance-checker#installation) for additional Installation notes

## Usage

```shell
$ compliance-checker -l
IOOS compliance checker available checker suites (code version):
  ...
  - gliderdac (x.x.x)
  ...
$ compliance-checker -t gliderdac [dataset_location]
```

See the [ioos/compliance-checker](https://github.com/ioos/compliance-checker) for additional Usage notes
