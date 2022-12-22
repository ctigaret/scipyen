from __future__ import print_function


def my_plugin_function():
    print("Hello world two")


def init_scipyen_plugin():
    return {__name__:(__file__,{'Example Menu|Plugin2':  my_plugin_function})}

