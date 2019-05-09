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


## Summary of the Checks
The checks have been designed to help data providers submit the highest quality data to the GliderDAC. Submitting uncompliant data to the DAC may result in services not working. For example, not providing the correct Sea Name in the GLobal atttributes may put your glider depoyment into the wrong region on the GliderMap. Not providing proper metadata about the platform and instruments, and attribution may prevent NCEI from archiving your data. And not making your files CF compliant could prevent the files from showing up on ERDDAP and THREDDS servers all together.

### High priority checks
Failures in these checks should be addressed before submitting to the GliderDAC!

- check_required_variables
- check_dimensions
- check_lat_lon_attributes
- check_time_attributes
- check_pressure_depth_attributes
- check_ctd_variable_attributes
- check_profile_variable_attributes_and_types
- check_global_attributes
- check_standard_names
- check_monotonically_increasing_time
- check_dim_no_data
- check_depth_array


### Medium priority checks:

- check_qc_variables
- check_primary_variable_attributes
- check_trajectory_variables
- check_container_variables
- check_qartod
- check_ancillary_variables
- check_dtype
- check_valid_min_dtype
- check_valid_max_dtype


### Low priority checks

- check_ioos_ra
- check_valid_lon
- check_ncei_tables

## Optional environment variables
Paths for cached text files for institution, project, instrument, and
platform authority tables can be set with the following environment variables

- `INSTITUTION_TABLE`
- `PROJECT_TABLE`
- `INSTRUMENT_TABLE`
- `PLATFORM_TABLE`

Additionally, a cached version of the NCEI `seanames.xml` file can be provided
with a filesystem path in `SEA_NAME_TABLE` environment variable.

The table below indicates the relationship of the environment variables for
cached table locations on disk to their usual remote locations.

Environment Variable | Remote Table Location
-------------------- | ---------------------
`INSTITUTION_TABLE` | https://gliders.ioos.us/ncei_authority_tables/institutions.txt
`PROJECT_TABLE` | https://gliders.ioos.us/ncei_authority_tables/projects.txt
`INSTRUMENT_TABLE` | https://gliders.ioos.us/ncei_authority_tables/instruments.txt
`PLATFORM_TABLE` | https://gliders.ioos.us/ncei_authority_tables/platforms.txt
`SEA_NAME_TABLE` | https://www.nodc.noaa.gov/General/NODC-Archive/seanames.xml
