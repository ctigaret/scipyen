'''
Example python module usable as pict plugin.
'''
from __future__ import print_function

__pict_plugin__ = None

import collections

def f1():
    '''example_plugin.f1
    
    Function with no parameters, returns None.
    '''
    print("Hello world")
    
def f2():
    '''example_plugin.f2
    
    Function with no parameters, returns an int.
    
    Written in python 2.7, no function annotation.
    '''
    a = 0

    return a

def f3(a=3, b=2, c=1, *args, **kwargs):
    '''example_plugin.f3
    
    Function with three positional prameters, all with default values, and also with
    variadic parameters and keyword parameters.
    
    Returns a numeric scalar.
    
    Written in python 2.7, no function annotation.
    '''
    print("a = %d, b = %d, c = %d" % (a,b,c))
    return c * (a + b)


def f4(a, b, c, *args, **kwargs):
    '''example_plugin.f4
    
    Function with three positional parameters without default values, variadic 
    parameters and keyword parameters.
    
    Returns a numeric scalar.
    
    Written in python 2.7, no function annotation.
    '''
    print(f4.__name__, 'a ', a)
    print(f4.__name__, 'b ', b)
    print(f4.__name__, 'c ', c)
    print(f4.__name__, 'args', args)
    print(f4.__name__, 'kwargs', kwargs)
    a = 0
    return a

def f5(arg1, arg2, arg3, *args, **kwargs):
    '''example_plugin.f5
    
    Like f4, returns a list.
    
    Written in python 2.7, no function annotation.
    '''
    print(f4.__name__, 'arg1', arg1)
    print(f4.__name__, 'arg2', arg2)
    print(f4.__name__, 'arg3', arg3)
    print(f4.__name__, 'args', args)
    print(f4.__name__, 'kwargs', kwargs)
    
    ret = [arg1, arg2]
    
    return ret
    

# this allows some of the mandatory arguments to be omitted, specifically, arg2
# and arg3, from the function call, in wich case they will assume the default values.
# I guess the only way to go about this is to advertise the complete list of formal 
# arguments to the plugin loader, regardless if they have a default value or not, 
# in the function definition
def f6(arg1=3.2, arg2='default value for arg2', arg3=44, *args, **kwargs):
    '''example_plugin.f6
    
    Function with positional parameters (all with default values), variadic
    parameters and keyword parameters.
    
    Returns a tuple with two variables.
    
    Written in python 2.7, no function annotation.
    '''
    print(f.__name__, 'arg1', arg1)
    print(f.__name__, 'arg2', arg2)
    print(f.__name__, 'arg3', arg3)
    print(f.__name__, 'args', args)
    print(f.__name__, 'kwargs', kwargs)
    
    return arg1, arg2

def f7(arg1, arg2='default value for arg2', arg3=44, *args, **kwargs):
    '''example_plugin.f7
    
    Like f6, but first parameter without default value, and has annotations 
    builtin.
    
    Note, annotations are NOT added here, but after the function object has been
    defined.
    '''
    return arg1, arg2

f7.__setattr__('__annotations__',{'return':('arg1','arg2'), 'arg1':int, 'arg2':str, 'arg3':int})
    
# NOTE: 2016-04-16 09:57:13
# tis can give fancy menu names
# this ridiculous example breaks things down when the function is being called
# somehere else in the code
#f2.__name__ = "function with wicked and illegal name"

f2.__name__ = "renamed_func"

def init_pict_plugin():
    ''' Sat Apr 16 2016 23:18:33 GMT+0100 (BST)
    Returns information about plugins functions to be installed as menu item
    "callbacks" in the main pict GUI window.
        
    TIP:
    use collections.OrdererDict instead of plain dict
    '''

    # NOTE: 2016-04-16 22:30:59 KEEP IT SIMPLE, STUPID !!!
    
    # NOTE: 2017-05-24 12:27:41 can't I get these signatures directly from the functions themselves?
    # otherwise this is error prone!
    submenu1 = collections.OrderedDict([(f1,[None,None]),\
                                        (f2,(1, None)),\
                                        (f4,(1, (int, float, str))),\
                                        (f6,(2, (float, str, int)))])

    submenu2 = collections.OrderedDict([(f3,(1, (int,int,int))),\
                                        (f4,(1, (float)))])
    
    menu     = collections.OrderedDict([('Example Plugins|Plugin|functions', submenu1),\
                                        ('Example Plugins|Plugin|function_3',submenu2),\
                                        ('Example Plugins|Plugin|Annotated function', f7)])
    
    return menu

    #ret      = collections.OrderedDict([(__name__,(__file__, menu))])
    

    #return {__name__:(__file__, {'Example Plugin|Plugin|functions':{f1:[None, None],\
                                                                    #f2:(1, None),\
                                                                    #f6:(2, (float, str, int))},\
                                 #'Example Plugin|Plugin|function_3':{f3:(1,(int,int,int)),\
                                                                     #f4:(1,float)}})}
                             

def __init__():
    print("example_plugin __init__")
    pass
