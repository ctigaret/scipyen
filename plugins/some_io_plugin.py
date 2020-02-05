from __future__ import print_function


def my_plugin_function():
    print("Foo bar")


def init_pict_plugin():
    return {__name__:(__file__, {'File|Open|Spam': my_plugin_function})}

