#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
cc_plugin_glider/util.py
'''
from pkg_resources import resource_filename
import csv


_SEA_NAMES = None


def get_sea_names():
    '''
    Returns a list of NODC sea names

    source of list: https://www.nodc.noaa.gov/General/NODC-Archive/seanamelist.txt
    '''
    global _SEA_NAMES
    if _SEA_NAMES is None:
        buf = {}
        with open(resource_filename('cc_plugin_glider', 'data/seanames.csv'), 'r') as f:
            reader = csv.reader(f)
            for code, sea_name in reader:
                buf[sea_name] = code
        _SEA_NAMES = buf
    return _SEA_NAMES
