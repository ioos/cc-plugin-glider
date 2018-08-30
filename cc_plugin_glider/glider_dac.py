#!/usr/bin/env python

'''
compliance_checker.glider_dac

Compliance Test Suite for the IOOS National Glider Data Assembly Center
https://github.com/ioos/ioosngdac/wiki
'''

from __future__ import (absolute_import, division, print_function)
from cc_plugin_glider import util
from compliance_checker import __version__
from compliance_checker.base import BaseCheck, BaseNCCheck, Result, TestCtx
import numpy as np

try:
    basestring
except NameError:
    basestring = str


class GliderCheck(BaseNCCheck):
    register_checker = True
    _cc_spec = 'gliderdac'
    _cc_spec_version = '3.0'
    _cc_checker_version = __version__
    _cc_url = 'https://github.com/ioos/ioosngdac/wiki/NGDAC-NetCDF-File-Format-Version-2'
    _cc_display_headers = {
        3: 'Required',
        2: 'Recommended',
        1: 'Suggested'
    }
    acceptable_platform_types = {
        'Seaglider',
        'Spray Glider',
        'Slocum Glider'
    }

    @classmethod
    def beliefs(cls):
        '''
        Not applicable for gliders
        '''
        return {}

    @classmethod
    def make_result(cls, level, score, out_of, name, messages):
        return Result(level, (score, out_of), name, messages)

    def setup(self, dataset):
        pass

    def check_locations(self, dataset):
        '''
        Validates that lat and lon are indeed variables
        '''
        level = BaseCheck.HIGH
        out_of = 1
        score = 0
        messages = []
        test = ('lat' in dataset.variables and 'lon' in dataset.variables)
        if test:
            score += 1
        else:
            messages.append("lat and lon don't exist")
        return self.make_result(level, score, out_of,
                                'Verifies lat and lon are variables', messages)

    def check_location_dimensions(self, dataset):
        '''
        Validates that lat and lon are valid timeseries variables
        '''
        level = BaseCheck.HIGH
        out_of = 26
        score = 0
        messages = []

        test = 'lat' in dataset.variables
        score += int(test)
        if not test:
            messages.append('lat is a required variable')
            return self.make_result(level, score, out_of,
                                    'Lat and Lon are Time Series', messages)

        test = 'lon' in dataset.variables
        score += int(test)
        if not test:
            messages.append('lon is a required variable')
            return self.make_result(level, score, out_of,
                                    'Lat and Lon are Time Series', messages)

        required_coordinate_attributes = [
            '_FillValue',
            'ancillary_variables',
            'comment',
            'coordinate_reference_frame',
            'long_name',
            'observation_type',
            'platform',
            'reference',
            'standard_name',
            'units',
            'valid_max',
            'valid_min'
        ]
        for attribute in required_coordinate_attributes:
            test = hasattr(dataset.variables['lat'], attribute)
            score += int(test)
            if not test:
                messages.append('%s attribute is required for lat' % attribute)

            test = hasattr(dataset.variables['lon'], attribute)
            score += int(test)
            if not test:
                messages.append('%s attribute is required for lat' % attribute)

        return self.make_result(level, score, out_of,
                                'Lat and Lon are Time Series', messages)

    def check_variables(self, dataset):
        '''
        Verifies the dataset has the required variables
        '''
        required_variables = [
            'trajectory',
            'time',
            'lat',
            'lon',
            'pressure',
            'depth',
            'temperature',
            'conductivity',
            'density',
            'profile_id',
            'profile_time',
            'profile_lat',
            'profile_lon',
            'time_uv',
            'lat_uv',
            'lon_uv',
            'u',
            'v',
            'platform',
            'instrument_ctd'
        ]
        level = BaseCheck.HIGH
        out_of = len(required_variables)
        score = 0
        messages = []
        for variable in required_variables:
            test = variable in dataset.variables
            score += int(test)
            if not test:
                messages.append("%s is a required variable" % variable)
        return self.make_result(level, score, out_of,
                                'Required Variables', messages)

    def check_qc_variables(self, dataset):
        '''
        Verifies the dataset has all the required QC variables
        '''
        test_ctx = TestCtx(BaseCheck.MEDIUM, 'QC Variables')
        qc_variables = [
            'time',
            'lat',
            'lon',
            'pressure',
            'depth',
            'temperature',
            'conductivity',
            'density',
            'profile_time',
            'profile_lat',
            'profile_lon',
            'time_uv',
            'lat_uv',
            'lon_uv',
            'u',
            'v'
        ]

        required_attributes = [
            'flag_meanings',
            'flag_values',
            'long_name',
            'standard_name',
            'valid_max',
            'valid_min'
        ]
        for variable in qc_variables:
            qc_var = '{}_qc'.format(variable)

            # QC varibles are no longer required
            if qc_var not in dataset.variables:
                continue

            for field in required_attributes:
                test = hasattr(dataset.variables[qc_var], field)
                test_ctx.assert_true(test,
                                     'variable {} must have a {} attribute'.format(qc_var, field))

        if test_ctx.out_of == 0:
            return None

        return test_ctx.to_result()

    def check_global_attributes(self, dataset):
        '''
        Verifies the base metadata in the global attributes
        '''
        attribute_fields = [
            'Conventions',
            'Metadata_Conventions',
            'comment',
            'contributor_name',
            'contributor_role',
            'creator_email',
            'creator_name',
            'creator_url',
            'date_created',
            'date_issued',
            'date_modified',
            'format_version',
            'history',
            'id',
            'institution',
            'keywords',
            'keywords_vocabulary',
            'license',
            'metadata_link',
            'naming_authority',
            # 'platform_type', # platform_type check is more involved below
            'processing_level',
            'project',
            'publisher_email',
            'publisher_name',
            'publisher_url',
            'references',
            # 'sea_name',  # sea_name check is more involved below
            'source',
            'standard_name_vocabulary',
            'summary',
            'title'
        ]
        level = BaseCheck.MEDIUM
        out_of = 0
        score = 0
        messages = []
        for field in attribute_fields:
            v = getattr(dataset, field, '')
            test = v != ''
            score += int(test)
            out_of += 1
            if not test:
                messages.append('%s global attribute is missing' % field)

            if isinstance(v, basestring):
                test = len(v.strip()) > 0
            else:
                test = True
            score += int(test)
            out_of += 1
            if not test:
                messages.append('%s global attribute can not be empty' % field)

        sea_names = [sn.lower() for sn in util.get_sea_names()]
        sea_name = getattr(dataset, 'sea_name', '').replace(', ', ',')
        if sea_name:
            # Ok score a point for the fact that the attribute exists
            score += 1
            out_of += 1
            sea_name = sea_name.split(',')
            for sea in sea_name:
                test = sea.lower() in sea_names
                score += int(test)
                out_of += 1
                if not test:
                    messages.append(('sea_name attribute should be from the NODC sea names list:'
                                     ' {} is not a valid sea name').format(sea))
        else:
            out_of += 1
            messages.append('sea_name global attribute is missing')

        # Check the platform type
        platform_type = getattr(dataset, 'platform_type', '')
        if platform_type:
            # Score a point for the fact that the attribute exists
            score += 1
            out_of += 1
            # Now check that it's one of the NCEI acceptable strings
            test = platform_type in self.acceptable_platform_types
            score += int(test)
            out_of += 1
            if not test:
                messages.append(('platform_type {} is not one of the NCEI accepted platforms for archiving: {}'
                                 ).format(platform_type, ",".join(self.acceptable_platform_types)))
        else:
            out_of += 1
            messages.append('platform_type global attribute is missing')

        return self.make_result(level, score, out_of,
                                'Recommended Global Attributes', messages)

    def check_wmo(self, dataset):
        '''
        Verifies that the data has a WMO ID but not necessarily filled out
        '''
        level = BaseCheck.MEDIUM
        score = 0
        out_of = 1
        messages = []
        test = hasattr(dataset, 'wmo_id')
        score += int(test)
        if not test:
            msg = ("WMO ID is a required attribute but can be empty if the"
                   "dataset doesn't have a WMO ID")
            messages.append(msg)

        return self.make_result(level, score, out_of, 'WMO ID', messages)

    def check_summary(self, dataset):
        level = BaseCheck.MEDIUM
        out_of = 1
        score = 0
        messages = []
        if hasattr(dataset, 'summary') and dataset.summary:
            score += 1
        else:
            messages.append('Dataset must define summary')
        return self.make_result(level, score, out_of,
                                'Summary defined', messages)

    def check_primary_variable_attributes(self, dataset):
        '''
        Verifies that each primary variable has the necessary metadata
        '''
        level = BaseCheck.MEDIUM
        out_of = 0
        score = 0
        messages = []
        primary_variables = [
            'lat',
            'lon',
            'pressure',
            'depth',
            'temperature',
            'conductivity',
            'salinity',
            'density',
            'profile_time',
            'profile_lat',
            'profile_lon',
            'time_uv',
            'lat_uv',
            'lon_uv',
            'u',
            'v'
        ]
        required_attributes = [
            '_FillValue',
            'units',
            'standard_name',
            'observation_type'
        ]
        for var in primary_variables:
            for attribute in required_attributes:
                test = hasattr(dataset.variables[var], attribute)
                out_of += 1
                score += int(test)
                if not test:
                    messages.append('%s variable is missing attribute %s' %
                                    (var, attribute))

        return self.make_result(level, score, out_of,
                                'Recommended Variable Attributes', messages)

    def check_dimensions(self, dataset):
        '''
        NetCDF files submitted by the individual glider operators contain 2
        dimension variables:
         - time
         - traj
        '''
        level = BaseCheck.HIGH
        score = 0
        messages = []

        required_dimensions = [
            'time',
            'traj_strlen'
        ]
        out_of = len(required_dimensions)

        for dimension in dataset.dimensions:
            test = dimension in required_dimensions
            score += int(test)
            if not test:
                messages.append('%s is not a valid dimension' % dimension)
        return self.make_result(level, score, out_of,
                                'Required Dimensions', messages)

    def check_trajectory_variables(self, dataset):
        '''
        The trajectory variable stores a character array that identifies the
        deployment during which the data was gathered. This variable is used by
        the DAC to aggregate all individual NetCDF profiles containing the same
        trajectory value into a single trajectory profile data set. This value
        should be a character array that uniquely identifies the deployment and
        each individual NetCDF file from the deployment data set should have
        the same value.
        '''
        level = BaseCheck.MEDIUM
        out_of = 5
        score = 0
        messages = []

        test = 'trajectory' in dataset.variables
        score += int(test)
        if not test:
            messages.append('trajectory variable not found')
            return self.make_result(level, score, out_of,
                                    'Trajectory Variable', messages)
        test = dataset.variables['trajectory'].dimensions == ('traj_strlen',)
        score += int(test)
        if not test:
            messages.append('trajectory has an invalid dimension')
        test = hasattr(dataset.variables['trajectory'], 'cf_role')
        score += int(test)
        if not test:
            messages.append('trajectory is missing cf_role')
        test = hasattr(dataset.variables['trajectory'], 'comment')
        score += int(test)
        if not test:
            messages.append('trajectory is missing comment')
        test = hasattr(dataset.variables['trajectory'], 'long_name')
        score += int(test)
        if not test:
            messages.append('trajectory is missing long_name')
        return self.make_result(level, score, out_of,
                                'Trajectory Variable', messages)

    def check_time_series_variables(self, dataset):
        '''
        Verifies that the time coordinate variable is correct
        '''

        level = BaseCheck.HIGH
        out_of = 7
        score = 0
        messages = []

        test = 'time' in dataset.variables
        score += int(test)
        if not test:
            messages.append('Required coordinate variable time is missing')
            return self.make_result(level, score, out_of,
                                    'Time Series Variable', messages)

        test = dataset.variables['time'].dtype.str == '<f8'
        score += int(test)
        if not test:
            msg = 'Invalid variable type for time, it should be float64'
            messages.append(msg)

        if hasattr(dataset.variables['time'], 'ancillary_variables'):
            out_of += 1
            acv = dataset.variables['time'].ancillary_variables
            test = acv in dataset.variables
            score += int(test)
            if not test:
                msg = ('Invalid ancillary_variables attribute for time, '
                       '{} is not a variable'.format(acv))
                messages.append(msg)

        test = dataset.variables['time'].calendar == 'gregorian'
        score += int(test)
        if not test:
            messages.append('Invalid calendar for time, should be "gregorian"')

        test = dataset.variables['time'].long_name == 'Time'
        score += int(test)
        if not test:
            messages.append('Invalid long_name for time, should be "Time"')

        test = dataset.variables['time'].observation_type == 'measured'
        score += int(test)
        if not test:
            msg = 'Invalid observation_type for time, should be "measured"'
            messages.append(msg)

        test = dataset.variables['time'].standard_name == 'time'
        score += int(test)
        if not test:
            messages.append('Invalid standard name for time, should be "time"')

        test = hasattr(dataset.variables['time'], 'units')
        score += int(test)
        if not test:
            messages.append('No units defined for time')

        return self.make_result(level, score, out_of,
                                'Time Series Variable', messages)

    def check_depth_coordinates(self, dataset):
        '''
        Verifies that the pressure coordinate/data variable is correct
        '''

        level = BaseCheck.HIGH
        out_of = 34
        score = 0
        messages = []

        coordinates = ['pressure', 'depth']

        for coordinate in coordinates:
            test = coordinate in dataset.variables
            score += int(test)

            if not test:
                messages.append('Required coordinate variable %s is missing' %
                                coordinate)
                return self.make_result(level, score, out_of,
                                        'Depth/Pressure Variables', messages)

        required_values = {
        }

        data_vars = {i: dataset.variables[i] for i in coordinates}
        for key, value in required_values.items():
            for data_var in data_vars:
                if not hasattr(data_vars[data_var], key):
                    messages.append('%s variable requires attribute %s with a value of %s' % (data_var, key, value))  # noqa
                    continue
                if not test:
                    messages.append('%s.%s != %s' % (data_var, key, value))
                    continue
                score += 1

        required_attributes = [
            '_FillValue',
            'ancillary_variables',
            'accuracy',
            'ancillary_variables',
            'comment',
            'instrument',
            'long_name',
            'platform',
            'positive',
            'precision',
            'reference_datum',
            'resolution',
            'standard_name',
            'units',
            'valid_max',
            'valid_min'
        ]

        for field in required_attributes:
            for data_var in data_vars:
                if not hasattr(data_vars[data_var], field):
                    messages.append('%s variable requires attribute %s' %
                                    (data_var, field))
                    continue
                score += 1

        return self.make_result(level, score, out_of,
                                'Depth/Pressure Variables', messages)

    def check_ctd_variables(self, dataset):
        '''
        Verifies that the CTD Variables are the correct data type and contain
        the correct metadata
        '''

        level = BaseCheck.HIGH
        out_of = 56
        score = 0
        messages = []

        variables = [
            'temperature',
            'conductivity',
            'salinity',
            'density'
        ]

        required_fields = [
            'accuracy',
            'ancillary_variables',
            'instrument',
            'long_name',
            'observation_type',
            'platform',
            'precision',
            'resolution',
            'standard_name',
            'units',
            'valid_max',
            'valid_min'
        ]

        for var in variables:
            if var not in dataset.variables:
                messages.append('%s variable missing' % var)
                continue
            nc_var = dataset.variables[var]

            test = nc_var.dtype.str == '<f8'
            score += int(test)
            if not test:
                messages.append('%s variable is incorrect data type' % var)

            for field in required_fields:
                if not hasattr(nc_var, field):
                    messages.append('%s variable is missing required attribute %s' % (var, field))  # noqa
                    continue
                score += 1

            score += 1
        return self.make_result(level, score, out_of, 'CTD Variables',
                                messages)

    def check_standard_names(self, dataset):
        '''
        Verifies that the standard names are correct.
        '''
        level = BaseCheck.MEDIUM
        out_of = 1
        score = 0
        messages = []
        std_names = {
            'salinity': 'sea_water_practical_salinity'
        }

        for var in std_names:
            if var not in dataset.variables:
                messages.append("Can't verify standard name for %s: %s is missing." % (var, var))  # noqa
                continue
            nc_var = dataset.variables[var]
            test = getattr(nc_var, 'standard_name', None) == std_names[var]
            score += int(test)
            if not test:
                messages.append("Invalid standard name for %s: %s" %
                                (var, getattr(nc_var, 'standard_name', '')))

        return self.make_result(level, score, out_of,
                                'Standard Names', messages)

    def check_profile_vars(self, dataset):
        '''
        Verifies that the profile variables are the of the correct data type
        and contain the correct metadata
        '''

        level = BaseCheck.MEDIUM
        out_of = 74
        score = 0
        messages = []

        data_struct = {
            'profile_id': {
                'dtype': '<i4',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'valid_min',
                    'valid_max'
                ]
            },
            'profile_time': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units'
                ]
            },
            'profile_lat': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units',
                    'valid_min',
                    'valid_max'
                ]
            },
            'profile_lon': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units',
                    'valid_min',
                    'valid_max'
                ]
            },
            'lat_uv': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units',
                    'valid_min',
                    'valid_max'
                ]
            },
            'lon_uv': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units',
                    'valid_min',
                    'valid_max'
                ]
            },
            'u': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units',
                    'valid_min',
                    'valid_max'
                ]
            },
            'v': {
                'dtype': '<f8',
                'fields': [
                    '_FillValue',
                    'comment',
                    'long_name',
                    'observation_type',
                    'platform',
                    'standard_name',
                    'units',
                    'valid_min',
                    'valid_max'
                ]
            }
        }

        for profile_var in data_struct:
            test = profile_var in dataset.variables
            if not test:
                messages.append("Required Variable %s is missing" %
                                profile_var)
                continue

            nc_var = dataset.variables[profile_var]
            dtype = np.dtype(data_struct[profile_var]['dtype'])
            test = nc_var.dtype.str == dtype.str
            score += int(test)
            if not test:
                messages.append('%s variable has incorrect dtype, should be %s' % (profile_var, dtype.name))  # noqa

            for field in data_struct[profile_var]['fields']:
                test = hasattr(nc_var, field)
                if not test:
                    messages.append('%s variable is missing required attribute %s' % (profile_var, field))  # noqa
                    continue
                score += 1

        return self.make_result(level, score, out_of,
                                'Profile Variables', messages)

    def check_container_variables(self, dataset):
        '''
        Verifies that the dimensionless container variables are the correct
        data type and contain the required metadata
        '''

        level = BaseCheck.MEDIUM
        out_of = 19
        score = 0
        messages = []

        data_struct = {
            'platform': {
                'dtype': '<i4',
                'fields': [
                    '_FillValue',
                    'comment',
                    'id',
                    'instrument',
                    'long_name',
                    'type',
                    'wmo_id'
                ]
            },
            'instrument_ctd': {
                'dtype': '<i4',
                'fields': [
                    '_FillValue',
                    'calibration_date',
                    'calibration_report',
                    'comment',
                    'factory_calibrated',
                    'long_name',
                    'make_model',
                    'platform',
                    'serial_number',
                    'type'
                ]
            }
        }

        for container_var in data_struct:
            test = container_var in dataset.variables
            if not test:
                messages.append("Variable %s is missing" %
                                container_var)
                continue

            nc_var = dataset.variables[container_var]
            dtype = np.dtype(data_struct[container_var]['dtype'])
            test = nc_var.dtype.str == dtype.str
            score += int(test)
            if not test:
                messages.append('%s variable has incorrect dtype, should be %s' % (container_var, dtype.name))  # noqa

            for field in data_struct[container_var]['fields']:
                test = hasattr(nc_var, field)
                if not test:
                    messages.append('%s variable is missing required attribute %s' % (container_var, field))  # noqa
                    continue
                score += 1

        return self.make_result(level, score, out_of,
                                'Container Variables', messages)

    def check_qartod(self, dataset):
        '''
        If the qartod variables exist, check the attributes
        '''
        test_ctx = TestCtx(BaseCheck.MEDIUM, 'QARTOD Variables')
        qartod_variables = [
            'qartod_{}_climatological_flag',
            'qartod_{}_flat_line_flag',
            'qartod_{}_gross_range_flag',
            'qartod_{}_rate_of_chagne_flag',
            'qartod_{}_spike_flag'
        ]

        # Iterate through each physical variable and each qartod variable name
        # and check the attributes of all variables if they exist

        for param in ('temperature', 'conductivity', 'density', 'pressure'):
            for qartod in qartod_variables:
                qartod_var = qartod.format(param)
                if qartod_var not in dataset.variables:
                    continue

                ncvar = dataset.variables[qartod_var]
                valid_min = getattr(ncvar, 'valid_min', None)
                valid_max = getattr(ncvar, 'valid_max', None)
                flag_values = getattr(ncvar, 'flag_values', None)
                test_ctx.assert_true(getattr(ncvar, '_FillValue', None) == np.int8(9),
                                     'variable {} must have a _FillValue of 9b'.format(qartod_var))

                test_ctx.assert_true(getattr(ncvar, 'long_name', ''),
                                     'attribute {}:long_name must be a non-empty string'
                                     ''.format(qartod_var))

                test_ctx.assert_true(getattr(ncvar, 'flag_meanings', ''),
                                     'attribute {}:flag_meanings must be a non-empty string'
                                     ''.format(qartod_var))

                test_ctx.assert_true(isinstance(flag_values, np.ndarray),
                                     'attribute {}:flag_values must be defined as an array of bytes'
                                     ''.format(qartod_var))

                if isinstance(flag_values, np.ndarray):
                    dtype = flag_values.dtype.str
                    test_ctx.assert_true(dtype == '|i1',
                                         'attribute {}:flag_values has an illegal data-type, must '
                                         'be byte'.format(qartod_var))

                valid_min_dtype = getattr(valid_min, 'dtype', None)
                test_ctx.assert_true(getattr(valid_min_dtype, 'str', None) == '|i1',
                                     'attribute {}:valid_min must be of type byte'
                                     ''.format(qartod_var))

                valid_max_dtype = getattr(valid_max, 'dtype', None)
                test_ctx.assert_true(getattr(valid_max_dtype, 'str', None) == '|i1',
                                     'attribute {}:valid_max must be of type byte'
                                     ''.format(qartod_var))

        if test_ctx.out_of == 0:
            return None

        return test_ctx.to_result()

    def check_ioos_ra(self, dataset):
        '''
        Check if the ioos_regional_association attribute exists, if it does check that it's not
        empty
        '''
        test_ctx = TestCtx(BaseCheck.LOW, 'IOOS Regional Association Attribute')

        ioos_ra = getattr(dataset, 'ioos_regional_association', None)

        test_ctx.assert_true(ioos_ra,
                             'ioos_regional_association global attribute should be defined')

        return test_ctx.to_result()

    def check_valid_min_dtype(self, dataset):
        '''
        Check that the valid attributes are valid data types
        '''
        test_ctx = TestCtx(BaseCheck.MEDIUM, 'Correct valid_min data types')

        for var_name in dataset.variables:
            ncvar = dataset.variables[var_name]

            valid_min = getattr(dataset.variables[var_name], 'valid_min', None)
            if isinstance(valid_min, basestring):
                valid_min_dtype = 'string'
            elif isinstance(valid_min, float):
                valid_min_dtype = 'float64'
            elif isinstance(valid_min, int):
                valid_min_dtype = 'int64'
            else:
                valid_min_dtype = str(getattr(valid_min, 'dtype', None))

            if valid_min is not None:
                test_ctx.assert_true(valid_min_dtype == str(ncvar.dtype),
                                     '{}:valid_min has a different data type, {}, than variable {} '
                                     '{}'.format(var_name, valid_min_dtype, str(ncvar.dtype),
                                                 var_name))

        return test_ctx.to_result()

    def check_valid_max_dtype(self, dataset):
        '''
        Check that the valid attributes are valid data types
        '''
        test_ctx = TestCtx(BaseCheck.MEDIUM, 'Correct valid_max data types')

        for var_name in dataset.variables:
            ncvar = dataset.variables[var_name]

            valid_max = getattr(dataset.variables[var_name], 'valid_max', None)
            if isinstance(valid_max, basestring):
                valid_max_dtype = 'string'
            elif isinstance(valid_max, float):
                valid_max_dtype = 'float64'
            elif isinstance(valid_max, int):
                valid_max_dtype = 'int64'
            else:
                valid_max_dtype = str(getattr(valid_max, 'dtype', None))

            if valid_max is not None:
                test_ctx.assert_true(valid_max_dtype == str(ncvar.dtype),
                                     '{}:valid_max has a different data type, {}, than variable {} '
                                     '{}'.format(var_name, valid_max_dtype, str(ncvar.dtype),
                                                 var_name))

        return test_ctx.to_result()

    def check_valid_lon(self, dataset):
        test_ctx = TestCtx(BaseCheck.MEDIUM, 'Longitude valid_min valid_max not [-90, 90]')

        if 'lon' not in dataset.variables:
            return

        longitude = dataset.variables['lon']
        valid_min = getattr(longitude, 'valid_min')
        valid_max = getattr(longitude, 'valid_max')
        test_ctx.assert_true(not(valid_min == -90 and valid_max == 90),
                             "Longitude's valid_min and valid_max are [-90, 90], it's likey this "
                             "was a mistake")
        return test_ctx.to_result()
