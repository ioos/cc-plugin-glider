"""
cc_plugin_glider/util.py
"""

from operator import eq

import numpy as np
from cf_units import Unit

from cc_plugin_glider.required_var_attrs import required_var_attrs


def compare_dtype(dt1, dt2):
    """
    Helper function to compare two numpy dtypes to see if they are equivalent
    aside from endianness.  Returns True if the two are equivalent, False
    otherwise.
    """
    # string types map directly to Python string.  Decompose into numpy types
    # otherwise
    return eq(
        *(
            dt if dt == str else dt.kind + str(dt.itemsize)
            for dt in (dt1, dt2)
        ),
    )


def _check_dtype(dataset, var_name):
    """
    Convenience method to check a variable datatype validity
    """
    score = 0
    out_of = 0
    messages = []
    if var_name not in dataset.variables:
        # No need to check the attrs if the variable doesn't exist
        return (score, out_of, messages)

    var = dataset.variables[var_name]
    var_dict = required_var_attrs.get(var_name, {})
    expected_dtype = var_dict.get("dtype", None)
    if expected_dtype is not None:
        out_of += 1
        score += 1
        if not compare_dtype(var.dtype, np.dtype(expected_dtype)):
            messages.append(
                f"Variable {var_name} is expected to have a dtype of "
                f"{expected_dtype}, instead has a dtype of {var.dtype}"
                "",
            )
            score -= 1
    # check that the fill value is of the expected dtype as well
    if hasattr(var, "_FillValue") and hasattr(var._FillValue, "dtype"):
        if not compare_dtype(var.dtype, var._FillValue.dtype):
            messages.append(
                f"Variable {var_name} _FillValue dtype does not "
                "match variable dtype"
                "",
            )
            out_of += 1

    return (score, out_of, messages)


def _check_variable_attrs(
    dataset,
    var_name,
    required_attributes=None,
    options=None,
):
    """
    Convenience method to check a variable attributes based on the
    expected_vars dict
    """
    score = 0
    out_of = 0
    messages = []
    if var_name not in dataset.variables:
        # No need to check the attrs if the variable doesn't exist
        return (score, out_of, messages)

    var = dataset.variables[var_name]

    # Get the expected attrs to check
    check_attrs = required_attributes or required_var_attrs.get(var_name, {})
    ignore_attributes = _get_option("ignore_attributes", options)

    if ignore_attributes is not None:
        for attr in ignore_attributes:
            if attr in check_attrs:
                del check_attrs[attr]

    var_attrs = set(var.ncattrs())
    for attr in check_attrs:
        if attr == "dtype":
            # dtype check is special, see above
            continue
        out_of += 1
        score += 1
        # Check if the attribute is present
        if attr not in var_attrs:
            messages.append(
                f"Variable {var_name} must contain attribute: {attr}" "",
            )
            score -= 1
            continue

        # Attribute exists, let's check if there was a value we need to compare against
        if check_attrs[attr] is not None:
            if getattr(var, attr) != check_attrs[attr]:
                # No match, this may be an error, but first an exception for units
                if attr == "units":
                    msg = (
                        f"Variable {var_name} units attribute must be "
                        f"convertible to {check_attrs[attr]}"
                    )
                    try:
                        cur_unit = Unit(var.units)
                        comp_unit = Unit(check_attrs[attr])
                        if not cur_unit.is_convertible(comp_unit):
                            messages.append(msg)
                            score -= 1
                    except ValueError:
                        messages.append(msg)
                        score -= 1
                else:
                    messages.append(
                        f"Variable {var_name} attribute {attr} must be {check_attrs[attr]}",
                    )
                    score -= 1
        else:
            # Final check to make sure the attribute isn't an empty string
            try:
                # try stripping whitespace, and return an error if empty
                att_strip = getattr(var, attr).strip()
                if not att_strip:
                    messages.append(
                        f"Variable {var_name} attribute {attr} is empty" "",
                    )
                    score -= 1
            except AttributeError:
                pass

    return (score, out_of, messages)


def _have_option(needle, option_haystack):
    """
    Helper function to determine if a user requested a specific
    option.

    Returns: True if an option was present, otherwise False
    """

    # Do the quick short-circuit fast test
    if needle in option_haystack:
        return True

    # There may be a more complex option argument passed
    # ignore_attribute:one,two,three
    for straw in option_haystack:
        if straw.startswith(needle):
            return True

    return False


def _get_option(needle, option_haystack):
    """
    Helper function to retrieve a user requested a specific
    option.

    Returns:
      if found a list():
        [needle] or if ignore_attributes:dis,and,dat => [dis, and, dat]
      if not found, None
    """

    # Do the quick short-circuit tests first
    if option_haystack is None:
        return None

    if needle in option_haystack:
        return list(needle)

    # There may be a more complex option argument passed
    # ignore_attribute:one,two,three
    for straw in option_haystack:
        if straw.startswith(needle):
            return straw.split(":")[1].split(",")

    return None
