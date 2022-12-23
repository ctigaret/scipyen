from __future__ import print_function

__scipyen_plugin__ = None

import collections


def my_plugin_function():
    print("Hello world")


def init_scipyen_plugin():
    return my_plugin_function
    #return {__name__:(__file__, {'Plugin3': my_plugin_function})}

    # menu     = collections.OrderedDict([('Example Plugins|Plugin|Annotated function', my_plugin_function)])
    # menu     = collections.OrderedDict([('Example Plugins|Plugin|Annotated function', my_plugin_function)])

    
    # return menu


