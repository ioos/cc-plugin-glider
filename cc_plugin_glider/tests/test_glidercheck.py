from __future__ import (absolute_import, division, print_function)

import unittest
from pkg_resources import resource_filename
from netCDF4 import Dataset

from ..glider_dac import GliderCheck

try:
    basestring
except NameError:
    basestring = str

static_files = {
    'glider_std': resource_filename('cc_plugin_glider', 'tests/data/gliders/IOOS_Glider_NetCDF_v2.0.nc'),  # noqa
    'bad_location': resource_filename('cc_plugin_glider', 'tests/data/gliders/bad_location.nc'),  # noqa
    'bad_qc': resource_filename('cc_plugin_glider', 'tests/data/gliders/bad_qc.nc'),  # noqa
    'bad_metadata': resource_filename('cc_plugin_glider', 'tests/data/gliders/bad_metadata.nc'),  # noqa
}


class TestGliderCheck(unittest.TestCase):
    # @see
    # http://www.saltycrane.com/blog/2012/07/how-prevent-nose-unittest-using-docstring-when-verbosity-2/
    def shortDescription(self):
        return None

    # Override __str__ and __repr__ behavior to show a copy-pastable
    # nosetest name for ion tests.
    #  ion.module:TestClassName.test_function_name
    def __repr__(self):
        name = self.id()
        name = name.split('.')
        if name[0] not in ["ion", "pyon"]:
            return "%s (%s)" % (name[-1], '.'.join(name[:-1]))
        else:
            return "%s ( %s )" % (name[-1], '.'.join(name[:-2]) + ":" + '.'.join(name[-2:]))  # noqa
    __str__ = __repr__

    def get_dataset(self, nc_dataset):
        '''
        Return a pairwise object for the dataset
        '''
        if isinstance(nc_dataset, basestring):
            nc_dataset = Dataset(nc_dataset, 'r')
            self.addCleanup(nc_dataset.close)
        return nc_dataset

    def setUp(self):
        self.check = GliderCheck()

    def test_location(self):
        '''
        Checks that a file with the proper lat and lon do work
        '''
        dataset = self.get_dataset(static_files['glider_std'])
        result = self.check.check_locations(dataset)
        self.assertTrue(result.value)

    def test_location_fail(self):
        '''
        Ensures the checks fail for location
        '''
        dataset = self.get_dataset(static_files['bad_location'])
        result = self.check.check_locations(dataset)
        self.assertEqual(result.value, (0, 1))

    def test_ctd_fail(self):
        '''
        Ensures the ctd checks fail for temperature
        '''
        dataset = self.get_dataset(static_files['bad_qc'])
        result = self.check.check_ctd_variables(dataset)
        self.assertEqual(result.value, (55, 56))

    def test_ctd_vars(self):
        '''
        Ensures the ctd checks for the correct file
        '''
        dataset = self.get_dataset(static_files['glider_std'])
        result = self.check.check_ctd_variables(dataset)
        self.assertEqual(result.value, (56, 56))

    def test_global_fail(self):
        '''
        Tests that the global checks fail where appropriate
        '''
        dataset = self.get_dataset(static_files['bad_qc'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (41, 64))

    def test_global(self):
        '''
        Tests that the global checks work
        '''
        dataset = self.get_dataset(static_files['glider_std'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (64, 64))

    def test_metadata(self):
        '''
        Tests that empty attributes fail
        '''
        dataset = self.get_dataset(static_files['bad_metadata'])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (41, 64))

    def test_standard_names(self):
        '''
        Tests that the standard names succeed/fail
        '''

        dataset = self.get_dataset(static_files['bad_metadata'])
        result = self.check.check_standard_names(dataset)
        self.assertEqual(result.value, (0, 1))

        dataset = self.get_dataset(static_files['glider_std'])
        result = self.check.check_standard_names(dataset)
        self.assertEqual(result.value, (1, 1))
