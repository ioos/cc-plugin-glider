"""
cc_plugin_glider/tests/test_glidercheck.py
"""

import os
import unittest
from urllib.parse import urljoin

import numpy as np
import requests_mock
from compliance_checker.tests.helpers import MockTimeSeries
from netCDF4 import Dataset

from cc_plugin_glider import util
from cc_plugin_glider.tests.resources import STATIC_FILES

from ..glider_dac import GliderCheck


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
        name = name.split(".")
        if name[0] not in ["ion", "pyon"]:
            return f"{name[-1]} ({'.'.join(name[:-1])})"
        else:
            return (
                f"{name[-1]} ({'.'.join(name[:-2])} : {'.'.join(name[-2:])})"
            )

    __str__ = __repr__

    def get_dataset(self, nc_dataset):
        """
        Return a pairwise object for the dataset
        """
        if isinstance(nc_dataset, str):
            nc_dataset = Dataset(nc_dataset, "r")
            self.addCleanup(nc_dataset.close)
        return nc_dataset

    def setUp(self):
        # set up authority tables to prevent needing to fetch resources over
        # network, deal with changes, etc
        with requests_mock.Mocker() as mock:
            # NCEI metadata content
            with open(
                os.path.join(
                    os.path.dirname(__file__),
                    "data",
                    "ncei_metadata.xml",
                ),
                encoding="utf8",
            ) as ncei_metadata_file:
                ncei_metadata_content = ncei_metadata_file.read()
            mock.get(
                "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:IOOS-NGDAC;view=xml;responseType=text/xml",
                text=ncei_metadata_content,
            )

            # seanames content
            with open(
                os.path.join(
                    os.path.dirname(__file__),
                    "data",
                    "seanames.xml",
                ),
                encoding="utf8",
            ) as seanames_file:
                seanames_content = seanames_file.read()
            mock.get(
                "https://www.ncei.noaa.gov/data/oceans/ncei/vocabulary/seanames.xml",
                text=seanames_content,
            )
            self.check = GliderCheck()

    def test_location(self):
        """
        Checks that a file with the proper lat and lon do work
        """
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        result = self.check.check_lat_lon_attributes(dataset)
        self.assertTrue(result.value)

    def test_location_fail(self):
        """
        Ensures the checks fail for location
        """
        dataset = self.get_dataset(STATIC_FILES["bad_location"])
        result = self.check.check_lat_lon_attributes(dataset)
        # File has no lat lon vars, so the test should skip
        self.assertEqual(result.value, (0, 0))

    def test_ctd_fail(self):
        """
        Ensures the ctd checks fail for temperature
        """
        dataset = self.get_dataset(STATIC_FILES["bad_qc"])
        self.check.setup(dataset)
        result = self.check.check_ctd_variable_attributes(dataset)
        self.assertEqual(result.value, (38, 52))

    def test_ctd_vars(self):
        """
        Ensures the ctd checks for the correct file
        """
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        self.check.setup(dataset)
        result = self.check.check_ctd_variable_attributes(dataset)
        self.assertIn(
            "Variable temperature attribute accuracy is empty",
            result.msgs,
        )

    def test_global_fail(self):
        """
        Tests that the global checks fail where appropriate
        """
        dataset = self.get_dataset(STATIC_FILES["bad_qc"])
        self.check.setup(dataset)
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (42, 64))

    def test_global(self):
        """
        Tests that the global checks work
        """
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value[0], result.value[1])

    def test_metadata(self):
        """
        Tests that empty attributes fail
        """
        dataset = self.get_dataset(STATIC_FILES["bad_metadata"])
        result = self.check.check_global_attributes(dataset)
        self.assertEqual(result.value, (41, 64))

    def test_standard_names(self):
        """
        Tests that a file with an invalid standard name is caught (temperature)
        """
        # This one should pass
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        results = self.check.check_standard_names(dataset)
        for each in results:
            self.assertEqual(each.value[0], each.value[1])

        # This will fail
        dataset = self.get_dataset(STATIC_FILES["bad_standard_name"])
        results = self.check.check_standard_names(dataset)
        score = 0
        out_of = 0
        for each in results:
            score += each.value[0]
            out_of += each.value[1]
        assert score < out_of
        # 10 vars checked
        assert len(results) == 10

    def test_units(self):
        """
        Tests that a fie with invalid units is caught (temperature)
        """
        dataset = self.get_dataset(STATIC_FILES["bad_units"])
        results = self.check.check_ctd_variable_attributes(dataset)

        self.assertIn(
            "Variable temperature units attribute must be convertible to degrees_C",
            results.msgs,
        )

    def test_valid_lon(self):
        dataset = self.get_dataset(STATIC_FILES["bad_metadata"])
        result = self.check.check_valid_lon(dataset)
        assert result.value == (0, 1)

        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        result = self.check.check_valid_lon(dataset)
        assert result.value == (1, 1)

    def test_ioos_ra(self):
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        result = self.check.check_ioos_ra(dataset)
        assert result.value == (0, 1)

        dataset = self.get_dataset(STATIC_FILES["glider_std3"])
        result = self.check.check_ioos_ra(dataset)
        assert result.value == (1, 1)

    def test_valid_min_dtype(self):
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        result = self.check.check_valid_min_dtype(dataset)
        assert result.value == (30, 32)

        dataset = self.get_dataset(STATIC_FILES["glider_std3"])
        result = self.check.check_valid_min_dtype(dataset)
        assert result.value == (58, 58)

    def test_valid_max_dtype(self):
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        result = self.check.check_valid_max_dtype(dataset)
        assert result.value == (30, 32)

        dataset = self.get_dataset(STATIC_FILES["glider_std3"])
        result = self.check.check_valid_max_dtype(dataset)
        assert result.value == (58, 58)

    def test_qc_variables(self):
        dataset = self.get_dataset(STATIC_FILES["glider_std"])
        self.check.setup(dataset)
        result = self.check.check_qc_variables(dataset)
        self.assertEqual(result.value[0], result.value[1])

        dataset = self.get_dataset(STATIC_FILES["glider_std3"])
        self.check.setup(dataset)
        result = self.check.check_qc_variables(dataset)
        self.assertEqual(result.value[0], result.value[1])

        dataset = self.get_dataset(STATIC_FILES["bad_qc"])
        self.check.setup(dataset)
        result = self.check.check_qc_variables(dataset)
        assert sorted(result.msgs) == [
            "Variable depth_qc must contain attribute: flag_meanings",
            "Variable depth_qc must contain attribute: flag_values",
            "Variable pressure_qc must contain attribute: long_name",
            "Variable pressure_qc must contain attribute: standard_name",
        ]

        dataset = self.get_dataset(STATIC_FILES["no_qc"])
        self.check.setup(dataset)
        result = self.check.check_qc_variables(dataset)
        self.assertEqual(result.value[0], result.value[1])

    def test_compare_string_var_dtype(self):
        """
        Checks that the special dtype comparison case for variable-length
        strings is checked properly.  Calling var.dtype on a variable-length
        string returns Python `str` type instead of a NumPy dtype
        """
        ts = MockTimeSeries()
        str_var = ts.createVariable("str_var", str, ("time",))
        self.assertTrue(util.compare_dtype(str_var.dtype, str))

    def test_time_series_variables(self):
        dataset = self.get_dataset(STATIC_FILES["no_qc"])
        result = self.check.check_time_attributes(dataset)
        self.assertEqual(result.value[0], result.value[1])

    def test_time_monotonically_increasing(self):
        """Checks that the time variable is monotonically increasing"""
        ts = MockTimeSeries()
        # first check failure case
        ts.variables["time"][:] = np.zeros(500)
        result = self.check.check_monotonically_increasing_time(ts)
        self.assertLess(result.value[0], result.value[1])
        # now make a monotonically increasing time variable
        ts.variables["time"][:] = np.linspace(1, 500, 500)
        result = self.check.check_monotonically_increasing_time(ts)
        self.assertEqual(result.value[0], result.value[1])

    def test_time_depth_non_nan(self):
        """
        Check that the cartesian product of time and depth coordinate variables
        have at least two non-NaN combinations
        """
        ts = MockTimeSeries()
        ts.variables["time"][0] = 0
        ts.variables["depth"][0] = 5
        # cartesian product should only contain one element and fail
        result = self.check.check_dim_no_data(ts)
        self.assertLess(result.value[0], result.value[1])
        # adding one more coordinate variable should make the number of passing
        # combinations equal to two, which should pass this check
        ts.variables["time"][1] = 1
        result = self.check.check_dim_no_data(ts)
        self.assertEqual(result.value[0], result.value[1])

    def test_depth_diff(self):
        """
        Checks that the sum of the first order difference over the start to
        the end time is non-negligible
        """
        ts = MockTimeSeries()
        ts.variables["depth"][:] = np.ma.array(np.zeros(500))
        result = self.check.check_depth_array(ts)
        self.assertLess(result.value[0], result.value[1])
        depth_arr = ts.variables["depth"][:] = np.ma.array(
            np.linspace(1, 500, 500),
        )
        result = self.check.check_depth_array(ts)
        # mark every other value as bad/_FillValue.  Diff should exclude the
        # masked points and result should pass
        depth_arr[:-1:2] = np.ma.masked
        ts.variables["depth"][:] = depth_arr
        self.assertEqual(result.value[0], result.value[1])
        # set all to flagged, which should max of empty array, which seems
        # to be zero under numpy's implementation.
        depth_arr[:] = np.ma.masked
        ts.variables["depth"][:] = depth_arr
        self.assertLessEqual(result.value[0], result.value[1])

    def test_seanames(self):
        """
        Tests that sea names error message appears
        """
        dataset = self.get_dataset(STATIC_FILES["bad_metadata"])
        result = self.check.check_global_attributes(dataset)
        self.assertIn(
            (
                "sea_name attribute should be from the NODC sea names list:"
                "   is not a valid sea name"
            ),
            result.msgs,
        )

    def test_platform_type(self):
        """
        Tests that platform_type check is applied
        """
        dataset = self.get_dataset(STATIC_FILES["bad_metadata"])
        result = self.check.check_global_attributes(dataset)
        self.assertIn(
            (
                "platform_type Slocum is not one of the NCEI accepted platforms for archiving: {}"
            ).format(",".join(self.check.acceptable_platform_types)),
            result.msgs,
        )

    def test_ncei_compliance(self):
        """Tests that the NCEI compliance suite works"""

        mock_nc_file = MockTimeSeries()
        mock_nc_file.project = "Mid-Atlantic Regional Association Coastal Ocean Observing System (MARACOOS)"
        mock_nc_file.institution = "National Oceanic and Atmospheric Administration"
        instrument_var = mock_nc_file.createVariable("instrument", "i", ())
        instrument_var.make_model = "sea-bird"
        mock_nc_file.variables["depth"].instrument = "instrument"
        mock_nc_file.variables["depth"].platform = "platform"
        platform_var = mock_nc_file.createVariable("platform", "i", ())
        platform_var.id = "bill"

        result = self.check.check_ncei_tables(mock_nc_file)
        # everything should pass here
        self.assertEqual(result.value[0], result.value[1])
        # now change to values that should fail
        mock_nc_file.project = "N/A"
        mock_nc_file.institution = "N/A"
        # set instrument_var make_model to something not contained in the
        # list
        instrument_var.make_model = "Unknown"
        platform_var.id = "No platform"
        # create a dummy variable which points to an instrument that doesn't
        # exist
        dummy_var = mock_nc_file.createVariable("dummy", "i", ())
        dummy_var.instrument = "nonexistent_var_name"
        dummy_var.platform = "nonexistent_var_name_2"
        result_fail = self.check.check_ncei_tables(mock_nc_file)
        expected_msg_set = {
            "Global attribute project value 'N/A' not contained in project authority table",
            "Global attribute institution value 'N/A' not contained in institution authority table",
            "Attribute make_model 'Unknown' for variable instrument not contained in instrument authority table",
            "Referenced instrument variable nonexistent_var_name does not exist",
            "Attribute id 'No platform' for variable platform not contained in platform authority table",
            "Referenced platform variable nonexistent_var_name_2 does not exist",
        }
        self.assertSetEqual(expected_msg_set, set(result_fail.msgs))
        # remove attributes which need to be checked to see if properly
        # detected
        del (
            instrument_var.make_model,
            platform_var.id,
            mock_nc_file.project,
            mock_nc_file.institution,
        )
        missing_attr_results = self.check.check_ncei_tables(mock_nc_file)
        expected_missing_msgs = {
            "Attribute project not in dataset",
            "Attribute institution not in dataset",
            "Attribute make_model should exist in variable instrument",
            "Attribute id should exist in variable platform",
        }
        # check that all the missing attribute messages are contained in the
        # test results
        self.assertTrue(
            expected_missing_msgs <= set(missing_attr_results.msgs),
        )

        for name in ("institution", "instrument", "platform", "project"):
            self.check.auth_tables[name] = None

        self.assertRaises(
            RuntimeError,
            self.check.check_ncei_tables,
            mock_nc_file,
        )
