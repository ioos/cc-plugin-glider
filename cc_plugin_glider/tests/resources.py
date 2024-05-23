"""
cc_plugin_glider/tests/resources.py
"""

import importlib
import subprocess


def get_filename(path):
    """
    Returns the path to a valid dataset
    """
    filename = importlib.resources.files("cc_plugin_glider") / path
    nc_path = filename.with_suffix(".nc")
    if not nc_path.exists():
        generate_dataset(filename, nc_path)
    return str(nc_path)


def generate_dataset(cdl_path, nc_path):
    subprocess.call(["ncgen", "-o", nc_path, cdl_path])


STATIC_FILES = {
    "bad_metadata": get_filename("tests/data/bad_metadata.cdl"),
    "glider_std": get_filename("tests/data/IOOS_Glider_NetCDF_v2.0.cdl"),
    "glider_std3": get_filename("tests/data/IOOS_Glider_NetCDF_v3.0.cdl"),
    "bad_location": get_filename("tests/data/bad_location.cdl"),
    "bad_qc": get_filename("tests/data/bad_qc.cdl"),
    "no_qc": get_filename("tests/data/no_qc.cdl"),
    "bad_standard_name": get_filename("tests/data/bad_standard_name.cdl"),
    "bad_units": get_filename("tests/data/bad_units.cdl"),
}
