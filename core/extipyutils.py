# -*- coding: utf-8 -*-
import sys, pickle, inspect
from functools import wraps
#from contextlib import contextmanager
#print(sys.path)

init_commands = ["import sys, os, io, warnings, numbers, types, typing, re, importlib",
                 "import traceback, keyword, inspect, weakref, itertools, typing, functools",
                 "import signal, pickle, json, csv",
                 "from importlib import reload",
                 "sys.path=['" + sys.path[0] +"'] + sys.path",
                 ]

def make_user_expression(**kwargs):
    """Generates a single user_expression string for execution in a remote kernel.

    The user_expressions parameter to the kernel local client's execute() is a 
    dict mapping some name (local to the calling namespace) to a command string
    that is to be evaluated in the remote kernel namespace. 
    
    user_expressions = {"output": expression_cmd}
    
    Upon execute() call, the remote kernel executes the 'expression_cmd' and
    the returned object is mapped to the "output" key in user_expression, 
    embedded in the 'execute_reply' message received from the remote kernel 
    via the kernel client's shell channel.
    
    The message received from the remote kernel contains:
    (NOTE that only the relevant key/value pairs are listed below)
    
    message["content"]["user_expressions"]: a dict with the following key/value
    pairs:
    
    local_name ->  user_sub_expression dict(): a nested dict with the key/value  pairs:
    
        "status" -> str = OK when the message passing from the kernel was successful
        
        "data" -> dict() -  with the mapping:
        
            "status" -> str = "ok" when 'expression_cmd' execution was successful
            
            "text/plain" -> str  = string representation of the result of 
                                    'expression_cmd' execution in the remote 
                                    kernel namespace. 
                                    
                                    This may be a byte array, when is the result 
                                    of serialization in the remote kernel
                                    namespace (see below).
                                    
    A successful execute(...) call is indicated when the next conditions are
    simultaneously satisfied:
    
        message["content"]["status"] == "ok"
        
        message["content"]["user_expressions"][local_name]["status"] == "ok"
        
    As stated above, the string representation of the result is in
    
    message["content"]["user_expressions"][local_name]["data"]["text/plain"]
    
    In the example above, local_name is "output".
                                    
    Sometimes it is useful to get the objects returned by evaluating 'expression_cmd',
    not just their string representation. This is possible only for objects that
    can be serialized (using the pickle module).
    
    In this case, 'expression_cmd' must instruct the remote kernel to "pack" 
    the remote execution result itself into a serializable object, such as a 
    dictionary, then pickle it (as bytes) to a string. 
    
    Such a "pickled" command has the (strict) syntax:
    
    "pickle.dumps({...})" 
    
        where {...} is the python text code for generating the dictionary in the
        remote kernel namespace
    
    For example, given the expression "dir()", the following:
    
        pickled_sub_expression_cmd = "pickle.dumps({'namespace': dir()})"
        
        binds the result of dir() (a list of str - the contents of the remote
        kernel namespace) to the symbol "namespace".
        
    In turn, the containing user_expression on the call side would be:
        {'namespace':pickled_sub_expression_cmd}
        
    and the string representation of the serialized dict 
        {"namespace":<result of dir()>} will be assigned to
    
        message["contents"]["user_expression"]["namespace"]["data"]["text/plain"]
        
        in the execute_reply message (provided execution was successful).
        
    Using a dictionary on the remote kernel "side" is not mandatory. A dict will
    bind the result to a symbol or a name, the key of the remote dictionary), 
    with the price that the result of the actual pickled expression of introducing
    a deeper level of nesting in the execute_reply message.
    
    
    This string (containing serialized bytes) is then mapped to the "text/plain"
    key in the "data" sub-dictionary of the particular user expression mapped
    to the appropriate local key name (in the example given here, "output")
    
    The serialized bytes will be placed as a string, in
    
        message["content"]["user_expressions"]["output"]["data"]["text/plain"]
    
    These can be deserialized in the calling namespace by executing pickle.loads(eval(x))
    
    where "x" is message["content"]["user_expressions"]["output"]["data"]["text/plain"]`
    
    
    Parameters:
    ----------
    **kwargs:
    
    
    
    Returns:
    --------
    
    A str with the contents of the expression_cmd
    
    
    Where:
        key is a quoted str (i.e. must evaluate to a string in the remote kernel)
        
        expression is a str that must evaliuate to a valid expression in the remote kernel
    
    """
    
    pass
    

def get_ipython_data_info_cmd(dataname:str):
    type_cmd = "'type':type("+dataname+").__name__"
    
    memsize_cmd = "'memsz':str(sys.getsizeof(" + dataname + "))"
    
    return [type_cmd, memsize_cmd]

def pickling(f, *args, **kwargs):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            cmds = f(*args, **kwargs)
            
            return cmds
            
        except:
            pass
            
    return wrapper
    

    #cmd = "pickle.dumps({"+ ",".join([cmds]) +"})"
    
    #return cmd


def put_data(dataname, data):
    datas = pickle.dumps({dataname:data})
    
    
