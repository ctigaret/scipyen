"""
LTP plugin -- TODO work in progress
"""

from __future__ import print_function

import collections

import ephys

def genMinuteAverages(base_prefix, chase_prefix, LTPOptions, test_ndx, result_name):
    return ephys.generate_minute_average_data(base_prefix, chase_prefix, LTPOptions, text_ndx, result_name)

genMinuteAverages.__setattr__("__annotations__", {"return":"ret", "base_prefix":str, "chase_prefix":str, "LTPOptions": dict, "test_ndx":int, "result_name": str})

def genLTPOptions():
    pass

def offlineLTP():
    pass




def init_pict_plugin():
    LTP_Offline_menu = collections.OrderedDict()
    return {"LTP|Offline|Analysis": offlineLTP}
