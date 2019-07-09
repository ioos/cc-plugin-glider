#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
cc_plugin_glider/util.py
'''
import csv
import numpy as np
from cc_plugin_glider.required_var_attrs import required_var_attrs
from cf_units import Unit
from operator import eq
from pkg_resources import resource_filename

def compare_dtype(dt1, dt2):
    '''
    Helper function to compare two numpy dtypes to see if they are equivalent
    aside from endianness.  Returns True if the two are equivalent, False
    otherwise.
    '''
    # string types map directly to Python string.  Decompose into numpy types
    # otherwise
    return eq(*(dt if dt == str else dt.kind + str(dt.itemsize)
                for dt in (dt1, dt2)))


def _check_dtype(dataset, var_name):
    '''
    Convenience method to check a variable datatype validity
    '''
    score = 0
    out_of = 0
    messages = []
    if var_name not in dataset.variables:
        # No need to check the attrs if the variable doesn't exist
        return (score, out_of, messages)

    var = dataset.variables[var_name]
    var_dict = required_var_attrs.get(var_name, {})
    expected_dtype = var_dict.get('dtype', None)
    if expected_dtype is not None:
        out_of += 1
        score += 1
        if not compare_dtype(var.dtype, np.dtype(expected_dtype)):
            messages.append('Variable {} is expected to have a dtype of '
                            '{}, instead has a dtype of {}'
                            ''.format(var_name, var.dtype, expected_dtype))
            score -= 1
    # check that the fill value is of the expected dtype as well
    if hasattr(var, '_FillValue') and hasattr(var._FillValue, 'dtype'):
        if not compare_dtype(var.dtype, var._FillValue.dtype):
            messages.append('Variable {} _FillValue dtype does not '
                            'match variable dtype'
                            ''.format(var_name, var._FillValue.dtype,
                                      var.dtype))
            out_of += 1

    return (score, out_of, messages)


def _check_variable_attrs(dataset, var_name, required_attributes=None):
    '''
    Convenience method to check a variable attributes based on the
    expected_vars dict
    '''
    score = 0
    out_of = 0
    messages = []
    if var_name not in dataset.variables:
        # No need to check the attrs if the variable doesn't exist
        return (score, out_of, messages)

    var = dataset.variables[var_name]

    # Get the expected attrs to check
    check_attrs = required_attributes or required_var_attrs.get(var_name, {})
    var_attrs = set(var.ncattrs())
    for attr in check_attrs:
        if attr == 'dtype':
            # dtype check is special, see above
            continue
        out_of += 1
        score += 1
        # Check if the attribute is present
        if attr not in var_attrs:
            messages.append('Variable {} must contain attribute: {}'
                            ''.format(var_name, attr))
            score -= 1
            continue

        # Attribute exists, let's check if there was a value we need to compare against
        if check_attrs[attr] is not None:
            if getattr(var, attr) != check_attrs[attr]:
                # No match, this may be an error, but first an exception for units
                if attr == 'units':
                    msg = ('Variable {} units attribute must be '
                           'convertible to {}'.format(var_name, check_attrs[attr]))
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
                    messages.append('Variable {} attribute {} must be {}'.format(var_name, attr, check_attrs[attr]))
                    score -= 1
        else:
            # Final check to make sure the attribute isn't an empty string
            try:
                # try stripping whitespace, and return an error if empty
                att_strip = getattr(var, attr).strip()
                if not att_strip:
                    messages.append('Variable {} attribute {} is empty'
                                    ''.format(var_name, attr))
                    score -= 1
            except AttributeError:
                pass

    return (score, out_of, messages)

