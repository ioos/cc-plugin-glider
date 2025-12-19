"""
cc_plugin_glider.glider_dac.py

Compliance Test Suite for the IOOS National Glider Data Assembly Center
https://ioos.github.io/glider-dac/
"""

import os
import warnings
from urllib.parse import urljoin

import numpy as np
import requests
from compliance_checker import __version__
from compliance_checker.base import BaseCheck, BaseNCCheck, Result, TestCtx
from compliance_checker.cf.cf import CF1_6Check
from io import BytesIO
from lxml import etree
from requests.exceptions import RequestException

from cc_plugin_glider import util


class GliderCheck(BaseNCCheck):
    register_checker = True
    _cc_spec = "gliderdac"
    _cc_spec_version = "3.0"
    _cc_checker_version = __version__
    _cc_url = "https://ioos.github.io/glider-dac/ngdac-netcdf-file-format-version-2.html"
    _cc_display_headers = {3: "Required", 2: "Recommended", 1: "Suggested"}
    acceptable_platform_types = {"Seaglider", "Spray Glider", "Slocum Glider"}

    def __init__(self, options=None):
        """
        Takes a set of options.
        """

        self.options = options
        iso_xml_location = "https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:IOOS-NGDAC;view=xml;responseType=text/xml"
        resp = requests.get(iso_xml_location, timeout=10)
        resp.raise_for_status()

        tree = etree.parse(BytesIO(resp.content))
        table_type = {
            "project": "NODC PROJECT NAMES THESAURUS",
            "platform": "NODC PLATFORM NAMES THESAURUS",
            "instrument": "Provider Instruments",
            "institution": "NODC COLLECTING INSTITUTION NAMES THESAURUS"
        }

        xpath_selector_template = ".//gmd:MD_Keywords[gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString/text()='{}']/gmd:keyword/{}/text()"
        namespaces = {"gco": "http://www.isotc211.org/2005/gco", "gmd": "http://www.isotc211.org/2005/gmd", "gmx": "http://www.isotc211.org/2005/gmx"}
        self.auth_tables = {}
        for global_att_name, text_content in table_type.items():
            text_elem = "gco:CharacterString" if global_att_name == "instrument" else "gmx:Anchor"
            self.auth_tables[global_att_name] = tree.xpath(xpath_selector_template.format(text_content, text_elem),
                                                           namespaces=namespaces)
        # handle NCEI sea names table
        sea_names_url = "https://www.ncei.noaa.gov/data/oceans/ncei/vocabulary/seanames.xml"

        def sea_name_parse(text):
            """Helper function to handle utf-8 parsing of sea name XML table"""
            utf8_parser = etree.XMLParser(encoding="utf-8")
            tree = etree.fromstring(text.encode("utf-8"), parser=utf8_parser)
            return set(tree.xpath("./seaname/seaname/text()"))

        self.auth_tables["sea_name"] = GliderCheck.request_resource(
            sea_names_url,
            os.environ.get("SEA_NAME_TABLE"),
            sea_name_parse,
        )

    @classmethod
    def request_resource(cls, url, backup_resource, fn):
        # TODO: check modify header vs cached version to see if update is
        # even necessary
        fail_flag = False
        if backup_resource is not None:
            try:
                with open(backup_resource) as f:
                    text_contents = f.read()
            except OSError:
                warnings.warn(
                    f"Could not open {backup_resource}, falling back to web request",
                    stacklevel=2,
                )
                fail_flag = True

        elif backup_resource is None or fail_flag:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10)
                resp.raise_for_status()
                text_contents = resp.text
            except RequestException:
                warnings.warn(
                    f"Requests exception encountered while fetching data from {url}",
                    stacklevel=2,
                )

        try:
            return fn(text_contents)
        except Exception as e:
            warnings.warn(
                f"Could not deserialize input text: {str(e)}",
                stacklevel=2,
            )
            return None

    cf_checks = CF1_6Check()

    @classmethod
    def make_result(cls, level, score, out_of, name, messages):
        return Result(level, (score, out_of), name, messages)

    def setup(self, dataset):
        self.dataset = dataset

    """
    HIGH priority checks:

    check_required_variables
    check_dimensions
    check_lat_lon_attributes
    check_time_attributes
    check_pressure_depth_attributes
    check_ctd_variable_attributes
    check_profile_variable_attributes_and_types
    check_global_attributes
    check_standard_names
    check_monotonically_increasing_time
    check_dim_no_data
    check_depth_array
    """

    def check_required_variables(self, dataset):
        """
        Verifies the dataset has the required variables
        """
        required_variables = [
            "trajectory",
            "time",
            "lat",
            "lon",
            "pressure",
            "depth",
            "temperature",
            "conductivity",
            "density",
            "profile_id",
            "profile_time",
            "profile_lat",
            "profile_lon",
            "time_uv",
            "lat_uv",
            "lon_uv",
            "u",
            "v",
            "platform",
            "instrument_ctd",
        ]

        level = BaseCheck.HIGH
        out_of = len(required_variables)
        score = 0
        messages = []
        for variable in required_variables:
            test = variable in dataset.variables
            score += int(test)
            if not test:
                messages.append(f"Variable {variable} is missing")
        return self.make_result(
            level,
            score,
            out_of,
            "Required Variables",
            messages,
        )

    def check_dimensions(self, dataset):
        """
        NetCDF files submitted by the individual glider operators contain 2
        dimension variables:
         - time
         - traj
        """
        level = BaseCheck.HIGH
        score = 0
        messages = []

        required_dimensions = ["time", "traj_strlen"]
        out_of = len(required_dimensions)

        for dimension in required_dimensions:
            test = dimension in dataset.dimensions
            score += int(test)
            if not test:
                messages.append(f"{dimension} is not a valid dimension")
        return self.make_result(
            level,
            score,
            out_of,
            "Required Dimensions",
            messages,
        )

    def check_lat_lon_attributes(self, dataset):
        """
        Validates that lat and lon have correct attributes

        For datasets without QARTOD flags, the option

        -o gliderdac:ignore_attributes:auxillary_variables

        may be used to avoid checker warnings about missing
        auxillary_variables but still allows other checks
        to continue against respective formats.

        TODO: Does this need to be its own check? Is it high priority?
        """
        level = BaseCheck.HIGH
        out_of = 0
        score = 0
        messages = []

        check_vars = ["lat", "lon"]
        for var in check_vars:
            stat, num_checks, msgs = util._check_variable_attrs(
                dataset,
                var,
                options=self.options,
            )
            score += int(stat)
            out_of += num_checks
            messages.extend(msgs)

        return self.make_result(
            level,
            score,
            out_of,
            "Lat and Lon attributes",
            messages,
        )

    def check_time_attributes(self, dataset):
        """
        Verifies that the time coordinate variable is correct
        """

        level = BaseCheck.HIGH
        score, out_of, messages = util._check_variable_attrs(dataset, "time")

        return self.make_result(
            level,
            score,
            out_of,
            "Time Variable",
            messages,
        )

    def check_pressure_depth_attributes(self, dataset):
        """
        Verifies that the pressure coordinate/data variable is correct.

        For datasets without QARTOD flags, the option

        -o gliderdac:ignore_attributes:auxillary_variables

        may be used to avoid checker warnings about missing
        auxillary_variables but still allows other checks
        to continue against respective formats.
        """

        level = BaseCheck.HIGH
        out_of = 0
        score = 0
        messages = []

        check_vars = ["pressure", "depth"]
        for var in check_vars:
            stat, num_checks, msgs = util._check_variable_attrs(
                dataset,
                var,
                options=self.options,
            )
            score += int(stat)
            out_of += num_checks
            messages.extend(msgs)

        return self.make_result(
            level,
            score,
            out_of,
            "Depth/Pressure variable attributes",
            messages,
        )

    def check_ctd_variable_attributes(self, dataset):
        """
        Verifies that the CTD Variables are the correct data type and contain
        the correct metadata.

        For datasets without QARTOD flags, the option

        -O gliderdac:ignore_attributes:auxillary_variables

        may be used to avoid checker warnings about missing
        auxillary_variables but still allows other checks
        to continue against respective formats.
        """
        level = BaseCheck.HIGH
        out_of = 0
        score = 0
        messages = []

        check_vars = ["temperature", "conductivity", "salinity", "density"]
        for var in check_vars:
            stat, num_checks, msgs = util._check_variable_attrs(
                dataset,
                var,
                options=self.options,
            )
            score += int(stat)
            out_of += num_checks
            messages.extend(msgs)
        return self.make_result(
            level,
            score,
            out_of,
            "CTD Variables",
            messages,
        )

    def check_profile_variable_attributes_and_types(self, dataset):
        """
        Verifies that the profile variables are the of the correct data type
        and contain the correct metadata.

        For datasets without QARTOD flags, the option

        -O gliderdac:ignore_attributes:auxillary_variables

        may be used to avoid checker warnings about missing
        auxillary_variables but still allows other checks
        to continue against respective formats.
        """

        level = BaseCheck.HIGH
        out_of = 0
        score = 0
        messages = []

        check_vars = [
            "profile_id",
            "profile_time",
            "profile_lat",
            "profile_lon",
            "lat_uv",
            "lon_uv",
            "u",
            "v",
        ]
        for var in check_vars:
            stat, num_checks, msgs = util._check_variable_attrs(
                dataset,
                var,
                options=self.options,
            )
            score += int(stat)
            out_of += num_checks
            messages.extend(msgs)

        return self.make_result(
            level,
            score,
            out_of,
            "Profile Variables",
            messages,
        )

    def check_global_attributes(self, dataset):
        """
        Verifies the base metadata in the global attributes

        TODO: update this check to use @check_has on next cc release
        """
        level = BaseCheck.HIGH
        global_attributes = [
            "Conventions",
            "Metadata_Conventions",
            "comment",
            "contributor_name",
            "contributor_role",
            "creator_email",
            "creator_name",
            "creator_url",
            "date_created",
            "date_issued",
            "date_modified",
            "format_version",
            "history",
            "id",
            "institution",
            "keywords",
            "keywords_vocabulary",
            "license",
            "metadata_link",
            "naming_authority",
            # 'platform_type', # platform_type check is more involved below
            "processing_level",
            "project",
            "publisher_email",
            "publisher_name",
            "publisher_url",
            "references",
            # 'sea_name',  # sea_name check is more involved below
            "source",
            "standard_name_vocabulary",
            "summary",
            "title",
            "wmo_id",
        ]

        out_of = 0
        score = 0
        messages = []
        for field in global_attributes:
            # v = getattr(dataset, field, '')
            test = field in dataset.ncattrs()
            score += int(test)
            out_of += 1
            if not test:
                messages.append(f"Attr {field} not present")
                continue
            v = getattr(dataset, field, "")
            if isinstance(v, str):
                test = len(v.strip()) > 0
            else:
                test = True
            score += int(test)
            out_of += 1
            if not test:
                messages.append(f"Attr {field} is empty")

        """
        Verify that sea_name attribute exists and is valid
        """
        if self.auth_tables["sea_name"] is not None:
            sea_names = {sn.lower() for sn in self.auth_tables["sea_name"]}
        else:
            raise RuntimeError("Was unable to fetch sea names table")
        sea_name = getattr(dataset, "sea_name", "").replace(", ", ",")
        if sea_name:
            # Ok score a point for the fact that the attribute exists
            score += 1
            out_of += 1
            sea_name = sea_name.split(",")
            for sea in sea_name:
                test = sea.lower() in sea_names
                score += int(test)
                out_of += 1
                if not test:
                    messages.append(
                        (
                            "sea_name attribute should be from the NODC sea names list:"
                            f" {sea} is not a valid sea name"
                        ),
                    )
        else:
            out_of += 1
            messages.append("Attr sea_name not present")

        """
        Verify that platform_type attribute exists and is valid
        """
        platform_type = getattr(dataset, "platform_type", "")
        if platform_type:
            # Score a point for the fact that the attribute exists
            score += 1
            out_of += 1
            # Now check that it's one of the NCEI acceptable strings
            test = platform_type in self.acceptable_platform_types
            score += int(test)
            out_of += 1
            if not test:
                messages.append(
                    (
                        "platform_type {} is not one of the NCEI accepted platforms for archiving: {}"
                    ).format(
                        platform_type,
                        ",".join(self.acceptable_platform_types),
                    ),
                )
        else:
            out_of += 1
            messages.append("Attr platform_type not present")

        return self.make_result(
            level,
            score,
            out_of,
            "Required Global Attributes",
            messages,
        )

    def check_standard_names(self, dataset):
        """
        Check a variables's standard_name attribute to ensure that it meets CF
        compliance.

        CF §3.3 A standard name is associated with a variable via the attribute
        standard_name which takes a string value comprised of a standard name
        optionally followed by one or more blanks and a standard name modifier

        :param netCDF4.Dataset dataset: An open netCDF dataset
        :return: List of results
        """
        results = self.cf_checks.check_standard_name(dataset)
        for dd in results:
            # Update the check name
            dd.name = "Standard Names"
        return results

    def check_monotonically_increasing_time(self, ds):
        """
        Check if all times are monotonically increasing
        """
        # shouldn't this already be handled by CF trajectory featureType?
        test_ctx = TestCtx(BaseCheck.HIGH, "Profile data is valid")
        test_ctx.assert_true(
            np.all(np.diff(ds.variables["time"]) > 0),
            "Time variable is not monotonically increasing",
        )
        return test_ctx.to_result()

    def check_dim_no_data(self, dataset):
        """
        Checks that cartesian product of the depth and time
        variables have more than 2 valid values.
        """
        test_ctx = TestCtx(BaseCheck.HIGH, "Profile data is valid")

        # check that cartesian product of non-nodata/_FillValue values >= 2
        # count here checks the count of non-masked data
        if "time" in dataset.variables and "depth" in dataset.variables:
            test = (
                dataset.variables["time"][:].count()
                * dataset.variables["depth"][:].count()
            ) >= 2
            test_ctx.assert_true(
                test,
                "Time and depth "
                "variables must have at least "
                "two valid data points together",
            )
        return test_ctx.to_result()

    def check_depth_array(self, dataset):
        """
        Checks that the profile data is valid (abs sum of diff > 0 for depth data)
        """
        test_ctx = TestCtx(BaseCheck.HIGH, "Profile data is valid")
        if "depth" in dataset.variables:
            depth = dataset.variables["depth"][:]
            test_ctx.assert_true(
                np.abs(np.diff(depth[~depth.mask]).sum()) > 1e-4,
                "Depth array must be valid, ie  abs(Z0 - Zend) > 0",
            )
        return test_ctx.to_result()

    """
    MEDIUM priority checks:

    check_qc_variables
    check_primary_variable_attributes
    check_trajectory_variables
    check_container_variables
    check_qartod
    check_ancillary_variables
    check_dtype
    check_valid_min_dtype
    check_valid_max_dtype
    """

    def check_qc_variables(self, dataset):
        """
        Verifies the dataset has all the required QC variables
        """
        level = BaseCheck.MEDIUM
        score = 0
        out_of = 0

        qc_variables = [
            f"{s}_qc"
            for s in [
                "time",
                "lat",
                "lon",
                "pressure",
                "depth",
                "temperature",
                "conductivity",
                "density",
                "profile_time",
                "profile_lat",
                "profile_lon",
                "time_uv",
                "lat_uv",
                "lon_uv",
                "u",
                "v",
            ]
        ]
        # The None means just check the attribute exists, not a value
        required_attributes = {
            "flag_meanings": None,
            "flag_values": None,
            "long_name": None,
            "standard_name": None,
            "valid_max": None,
            "valid_min": None,
        }
        messages = []
        for qc_var in qc_variables:
            pass_stat, num_checks, msgs = util._check_variable_attrs(
                dataset,
                qc_var,
                required_attributes,
            )
            out_of += num_checks
            score += int(pass_stat)
            messages.extend(msgs)
        return self.make_result(level, score, out_of, "QC Variables", messages)

    def check_trajectory_variables(self, dataset):
        """
        The trajectory variable stores a character array that identifies the
        deployment during which the data was gathered. This variable is used by
        the DAC to aggregate all individual NetCDF profiles containing the same
        trajectory value into a single trajectory profile data set. This value
        should be a character array that uniquely identifies the deployment and
        each individual NetCDF file from the deployment data set should have
        the same value.
        """
        level = BaseCheck.MEDIUM
        out_of = 0
        score = 0
        messages = []

        if "trajectory" not in dataset.variables:
            return

        test = dataset.variables["trajectory"].dimensions == ("traj_strlen",)
        score += int(test)
        out_of += 1
        if not test:
            messages.append("trajectory has an invalid dimension")

        pass_stat, num_checks, attr_msgs = util._check_variable_attrs(
            dataset,
            "trajectory",
        )
        score += int(pass_stat)
        out_of += num_checks
        messages.extend(attr_msgs)
        return self.make_result(
            level,
            score,
            out_of,
            "Trajectory Variable",
            messages,
        )

    def check_container_variables(self, dataset):
        """
        Verifies that the dimensionless container variables are the correct
        data type and contain the required metadata

        For datasets without QARTOD flags, the option

        -O gliderdac:ignore_attributes:auxillary_variables

        may be used to avoid checker warnings about missing
        auxillary_variables but still allows other checks
        to continue against respective formats.
        """

        level = BaseCheck.MEDIUM
        out_of = 0
        score = 0
        messages = []

        check_vars = [
            "platform",
            "instrument_ctd",
        ]
        for var in check_vars:
            stat, num_checks, msgs = util._check_variable_attrs(
                dataset,
                var,
                options=self.options,
            )
            score += int(stat)
            out_of += num_checks
            messages.extend(msgs)

        return self.make_result(
            level,
            score,
            out_of,
            "Container Variables",
            messages,
        )

    def check_qartod(self, dataset):
        """
        If the qartod variables exist, check the attributes
        """
        test_ctx = TestCtx(BaseCheck.MEDIUM, "QARTOD Variables")
        qartod_variables = [
            "qartod_{}_climatological_flag",
            "qartod_{}_flat_line_flag",
            "qartod_{}_gross_range_flag",
            "qartod_{}_rate_of_change_flag",
            "qartod_{}_spike_flag",
        ]

        # Iterate through each physical variable and each qartod variable name
        # and check the attributes of all variables if they exist

        for param in ("temperature", "conductivity", "density", "pressure"):
            for qartod in qartod_variables:
                qartod_var = qartod.format(param)
                if qartod_var not in dataset.variables:
                    continue

                ncvar = dataset.variables[qartod_var]
                valid_min = getattr(ncvar, "valid_min", None)
                # TODO: refactor valid_min/valid_max to put in single
                # conditional check
                test_ctx.assert_true(
                    valid_min is not None,
                    "valid_min attribute for longitude should be defined",
                )
                if valid_min is not None:
                    valid_min_dtype = getattr(valid_min, "dtype", None)
                    test_ctx.assert_true(
                        util.compare_dtype(valid_min_dtype, np.dtype("|i1")),
                        f"attribute {qartod_var}:valid_min must be of type byte",
                    )
                valid_max = getattr(ncvar, "valid_max", None)
                test_ctx.assert_true(
                    valid_max is not None,
                    "valid_max attribute for longitude should be defined",
                )
                if valid_max is not None:
                    valid_max_dtype = getattr(valid_max, "dtype", None)
                    test_ctx.assert_true(
                        util.compare_dtype(valid_max_dtype, np.dtype("|i1")),
                        f"attribute {qartod_var}:valid_max must be of type byte",
                    )
                flag_values = getattr(ncvar, "flag_values", None)
                test_ctx.assert_true(
                    getattr(ncvar, "_FillValue", None) == np.int8(9),
                    f"variable {qartod_var} must have a _FillValue of 9b",
                )

                test_ctx.assert_true(
                    getattr(ncvar, "long_name", ""),
                    f"attribute {qartod_var}:long_name must be a non-empty string",
                )

                test_ctx.assert_true(
                    getattr(ncvar, "flag_meanings", ""),
                    f"attribute {qartod_var}:flag_meanings must be a non-empty string",
                )

                test_ctx.assert_true(
                    isinstance(flag_values, np.ndarray),
                    f"attribute {qartod_var}:flag_values must be defined as an array of bytes",
                )

                if isinstance(flag_values, np.ndarray):
                    dtype = flag_values.dtype
                    test_ctx.assert_true(
                        util.compare_dtype(dtype, np.dtype("|i1")),
                        f"attribute {qartod_var}:flag_values has an illegal data-type, must be byte",
                    )


        if test_ctx.out_of == 0:
            return None

        return test_ctx.to_result()

    def check_ancillary_variables(self, dataset):
        """
        Check that the variables defined in ancillary_variables attribute exist
        """
        level = BaseCheck.MEDIUM
        out_of = 0
        score = 0
        messages = []

        check_vars = dataset.variables
        for var in check_vars:
            if hasattr(dataset.variables[var], "ancillary_variables"):
                ancillary_variables = dataset.variables[
                    var
                ].ancillary_variables
                for acv in ancillary_variables.split():
                    out_of += 1
                    test = acv in dataset.variables
                    score += int(test)
                    if not test:
                        msg = f"Invalid ancillary_variables attribute for {var}, {acv} is not a variable"
                        messages.append(msg)

        return self.make_result(
            level,
            score,
            out_of,
            "Ancillary Variables",
            messages,
        )

    def check_dtype(self, dataset):
        """
        Check that variables are of the correct datatype
        """
        level = BaseCheck.MEDIUM
        out_of = 0
        score = 0
        messages = []

        check_vars = dataset.variables
        for var in check_vars:
            stat, num_checks, msgs = util._check_dtype(dataset, var)
            score += int(stat)
            out_of += num_checks
            messages.extend(msgs)

        return self.make_result(
            level,
            score,
            out_of,
            "Correct variable data types",
            messages,
        )

    def check_valid_min_dtype(self, dataset):
        """
        Check that the valid attributes are valid data types
        """
        test_ctx = TestCtx(BaseCheck.MEDIUM, "Correct valid_min data types")

        for var_name in dataset.variables:
            ncvar = dataset.variables[var_name]

            valid_min = getattr(dataset.variables[var_name], "valid_min", None)
            if isinstance(valid_min, str):
                valid_min_dtype = "string"
            elif isinstance(valid_min, float):
                valid_min_dtype = "float64"
            elif isinstance(valid_min, int):
                valid_min_dtype = "int64"
            else:
                valid_min_dtype = str(getattr(valid_min, "dtype", None))

            if valid_min is not None:
                test_ctx.assert_true(
                    util.compare_dtype(np.dtype(valid_min_dtype), ncvar.dtype),
                    f"{var_name}:valid_min has a different data type, {valid_min_dtype}, than variable {var_name}, {ncvar.dtype}",
                )

        return test_ctx.to_result()

    def check_valid_max_dtype(self, dataset):
        """
        Check that the valid attributes are valid data types
        """
        test_ctx = TestCtx(BaseCheck.MEDIUM, "Correct valid_max data types")

        for var_name in dataset.variables:
            ncvar = dataset.variables[var_name]

            valid_max = getattr(dataset.variables[var_name], "valid_max", None)
            if isinstance(valid_max, str):
                valid_max_dtype = "string"
            elif isinstance(valid_max, float):
                valid_max_dtype = "float64"
            elif isinstance(valid_max, int):
                valid_max_dtype = "int64"
            else:
                valid_max_dtype = str(getattr(valid_max, "dtype", None))

            if valid_max is not None:
                test_ctx.assert_true(
                    util.compare_dtype(np.dtype(valid_max_dtype), ncvar.dtype),
                    f"{var_name}:valid_max has a different data type, {valid_max_dtype}, than variable {str(ncvar.dtype)} "
                    f"{var_name}",
                )

        return test_ctx.to_result()

    """
    LOW priority checks:

    check_ioos_ra
    check_valid_lon
    check_ncei_tables
    """

    def check_ioos_ra(self, dataset):
        """
        Check if the ioos_regional_association attribute exists, if it does check that it's not
        empty
        """
        test_ctx = TestCtx(
            BaseCheck.LOW,
            "IOOS Regional Association Attribute",
        )

        ioos_ra = getattr(dataset, "ioos_regional_association", None)

        test_ctx.assert_true(
            ioos_ra,
            "ioos_regional_association global attribute should be defined",
        )

        return test_ctx.to_result()

    def check_valid_lon(self, dataset):
        """
        Check the valid_min and valid max for longitude variable
        """
        test_ctx = TestCtx(
            BaseCheck.LOW,
            "Longitude valid_min valid_max not [-90, 90]",
        )

        if "lon" not in dataset.variables:
            return

        longitude = dataset.variables["lon"]
        valid_min = getattr(longitude, "valid_min", None)
        if valid_min is None:
            test_ctx.assert_true(
                False,
                "valid_min attribute for longitude should be defined",
            )
        valid_max = getattr(longitude, "valid_max", None)
        if valid_min is None:
            test_ctx.assert_true(
                False,
                "valid_max attribute for longitude should be defined",
            )
        test_ctx.assert_true(
            not (valid_min == -90 and valid_max == 90),
            "Longitude's valid_min and valid_max are [-90, 90], it's likely this was a mistake",
        )
        return test_ctx.to_result()

    def check_ncei_tables(self, dataset):
        """
        Checks the project, platform id, instrument make_model, and institution
        against lists of values provided by NCEI
        """
        test_ctx = TestCtx(
            BaseCheck.LOW,
            "File has NCEI approved project, "
            "institution, platform_type, and "
            "instrument",
        )
        # might refactor if the authority tables names change
        table_type = {
            "project": "projects.txt",
            "platform": "platforms.txt",
            "instrument": "instruments.txt",
            "institution": "institutions.txt",
        }
        # some top level attrs map to other things
        var_remap = {"platform": "id", "instrument": "make_model"}

        for global_att_name in table_type:
            # instruments have to be handled specially since they aren't
            # global attributes
            if global_att_name not in {"instrument", "platform"}:
                global_att_present = hasattr(dataset, global_att_name)
                test_ctx.assert_true(
                    global_att_present,
                    f"Attribute {global_att_name} not in dataset",
                )
                if not global_att_present:
                    continue

            if global_att_name not in {"instrument", "platform"}:
                global_att_present = hasattr(dataset, global_att_name)
                test_ctx.assert_true(
                    global_att_present,
                    f"Attribute {global_att_name} not in dataset",
                )
                if not global_att_present:
                    continue

            if self.auth_tables[global_att_name] is not None:
                check_set = self.auth_tables[global_att_name]
            else:
                raise RuntimeError(
                    f"Was unable to fetch {global_att_name} table",
                )

            # not truly a global attribute here, needs special handling for
            # instrument case
            if global_att_name in {"instrument", "platform"}:
                # variables which contain an instrument attribute,
                # which should point to an instrument variable
                kwargs = {global_att_name: lambda v: v is not None}
                att_vars = dataset.get_variables_by_attributes(**kwargs)
                # potentially, there could be more than one instrument
                var_name_set = {getattr(v, global_att_name) for v in att_vars}

                # treat no instruments/platforms defined as an error
                test_ctx.assert_true(
                    len(var_name_set) > 0,
                    f"Cannot find any {global_att_name} attributes in dataset",
                )

                for var_name in var_name_set:
                    if var_name not in dataset.variables:
                        msg = f"Referenced {global_att_name} variable {var_name} does not exist"
                        test_ctx.assert_true(False, msg)
                        continue

                    var = dataset.variables[var_name]
                    # have to use .ncattrs, hangs if using `in var` ?
                    var_attr_exists = (
                        var_remap[global_att_name] in var.ncattrs()
                    )
                    msg = f"Attribute {var_remap[global_att_name]} should exist in variable {var_name}"
                    test_ctx.assert_true(var_attr_exists, msg)

                    if not var_attr_exists:
                        continue
                    search_attr = getattr(var, var_remap[global_att_name])

                    msg = f"Attribute {var_remap[global_att_name]} '{search_attr}' for variable {var_name} not contained in {global_att_name} authority table"
                    test_ctx.assert_true(search_attr in check_set, msg)

            else:
                # check for global attribute existence already handled above
                global_att_value = getattr(dataset, global_att_name)
                msg = f"Global attribute {global_att_name} value '{global_att_value}' not contained in {global_att_name} authority table"
                test_ctx.assert_true(global_att_value in check_set, msg)

        return test_ctx.to_result()
