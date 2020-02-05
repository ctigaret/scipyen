from __future__ import print_function

__pict_plugin__ = None

import collections


def my_plugin_function():
    print("Hello world three")


def init_pict_plugin():
    #return {__name__:(__file__, {'Plugin3': my_plugin_function})}


    menu     = collections.OrderedDict([('Example Plugins|Plugin|Annotated function', my_plugin_function)])
    
    return menu


