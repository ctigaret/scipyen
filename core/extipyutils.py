# -*- coding: utf-8 -*-
"""Module with utilities for an external IPython kernel.
To be used on the client side (i.e. Scipyen app side)
"""
# on the client side, in a received execute_reply message the keys of
# msg["content"]["user_expressions"] are identical to those in the
# sent execute_request message["content"]["user_expressions"] NOTE that such
# execute_request message is sent when client.execute(...) is called, and the 
# user_expressions field of the message gets the valueof the user_expressions
# parameter ot that call.

import os, sys, pickle, inspect
from functools import wraps
#from contextlib import contextmanager
#print(sys.path)

__module_path__ = os.path.abspath(os.path.dirname(__file__))

# NOTE: 2016-04-03 00:17:42
__module_name__ = os.path.splitext(os.path.basename(__file__))[0]

nrn_ipython_initialization_file = os.path.join(os.path.dirname(__module_path__),"neuron_python", "nrn_ipython.py")
nrn_ipython_initialization_cmd = "".join(["run -i -n ", nrn_ipython_initialization_file])

init_commands = ["import sys, os, io, warnings, numbers, types, typing, re, importlib",
                 "import traceback, keyword, inspect, itertools, functools, collections",
                 "import signal, pickle, json, csv",
                 "from importlib import reload",
                 "".join(["sys.path.insert(2, '", os.path.dirname(__module_path__), "')"]),
                 #"from IPython.lib.deepreload import reload as dreload",
                 #"sys.path=['" + sys.path[0] +"'] + sys.path",
                 ]

def make_user_expression(**kwargs):
    """Generates a single user_expressions string for execution in a remote kernel.

    The user_expressions parameter to the kernel local client's execute() is a 
    dict mapping some name (local to the calling namespace) to a command string
    that is to be evaluated in the remote kernel namespace. 
    
    user_expressions = {"output": expression_cmd}
    
    Upon execute() call, the remote kernel executes the 'expression_cmd' and
    the returned object is mapped to the "output" key in user_expressions, 
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
        
    In turn, the containing user_expressions on the call side would be:
        {'namespace':pickled_sub_expression_cmd}
        
    and the string representation of the serialized dict 
        {"namespace":<result of dir()>} will be assigned to
    
        message["contents"]["user_expressions"]["namespace"]["data"]["text/plain"]
        
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

def pickle_wrap_expr(expr):
    if not isinstance(expr, str):
        raise TypeError("expecting a str, got %s" % type(expr).__name__)
    
    return "".join(["pickle.dumps(",expr,")"])
    

def get_ipython_data_info_cmd(dataname:str):
    type_cmd = "'type':type("+dataname+").__name__"
    
    memsize_cmd = "'memsz':str(sys.getsizeof(" + dataname + "))"
    
    return [type_cmd, memsize_cmd]

def cmd_request_remote_variable(varname:str) -> dict:
    return {"pickled_%s" % varname:"".join(["pickle.dumps({'",
                               varname,"':",
                               varname,"})",
                                ])}

def cmd_request_remote_variables(*args) -> dict:
    import itertools
    vardicts = (cmd_request_remote_variable(arg) for arg in args)
    return dict((x for x in itertools.chain(*(a.items() for a in vardicts))))

def unpack_received_remote_variable(msg:dict) -> dict:
    ret = dict()
    # peel-off layers one by one so we can always be clear of what this does
    msg_status = msg["content"]["status"]
    usr_expr = msg["content"]["user_expressions"]
    if msg_status == "ok":
        for key, value in usr_expr.items():
            #value = usr_expr[key]
            value_status = value["status"]
            if value_status == "ok":
                data_str = value["data"]["text/plain"] # this nested dict exists only if value_status is OK
                if key.startswith("pickled_"): # by OUR OWN convention, see cmd_request_remote_variable
                    data_dict = pickle.loads(eval(data_str))
                    
                else:
                    data_dict = {key:eval(data_str)}
                    
                ret.update(data_dict)
                
            
            elif value_status == "error":
                ret.update({"error_%s" % key: {"ename":value["ename"],
                                      "evalue": value["evalue"],
                                      "traceback": value["traceback"]}})
                #print("Exception name: %s" % value["ename"])
                #print("Exception value: %s" % value["evalue"])
                #print("\n".join(value["traceback"]))
                
            else:
                ret.update({"%s_%s" % (value_status, key): value_status})
                    
    elif msg_status == "error":
        ret.update({"error_%s" % msg["msg_type"]: {"ename": msg["content"]["ename"],
                                                  "evalue": msg["content"]["evalue"],
                                                  "traceback": msg["content"]["traceback"]}})
        #print("Exception name: %s" % msg["content"]["ename"])
        #print("Exception value: %s" % msg["content"]["evalue"])
        #print("\n".join(msg["content"]["traceback"]))
        
    else:
        ret.update({"%s_%s" % (msg_status, msg["msg_type"]): msg_status})
    
    return ret

#def pickling(f, *args, **kwargs):
    #@wraps(f)
    #def wrapper(*args, **kwargs):
        #try:
            #cmds = f(*args, **kwargs)
            
            #return cmds
            
        #except:
            #pass
            
    #return wrapper
    

    #cmd = "pickle.dumps({"+ ",".join([cmds]) +"})"
    
    #return cmd


def put_data(dataname, data):
    datas = pickle.dumps({dataname:data})
    
def execute(client, *args, **kwargs):
    """Execute code in the kernel, sent via the specified kernel client.
        
    Parameters
    ----------
    client: a kernel client
    
    *args, **kwargs - passed directly to client.execute(...), are as follows:
    
        code : str
        
            A string of code in the kernel's language.
        
        silent : bool, optional (default False)
            If set, the kernel will execute the code as quietly possible, and
            will force store_history to be False.
        
        store_history : bool, optional (default True)
            If set, the kernel will store command history.  This is forced
            to be False if silent is True.
        
        user_expressions : dict, optional
            A dict mapping names to expressions to be evaluated in the user's
            dict. The expression values are returned as strings formatted using
            :func:`repr`.
        
        allow_stdin : bool, optional (default self.allow_stdin)
            Flag for whether the kernel can send stdin requests to frontends.
        
            Some frontends (e.g. the Notebook) do not support stdin requests.
            If raw_input is called from code executed from such a frontend, a
            StdinNotImplementedError will be raised.
        
        stop_on_error: bool, optional (default True)
            Flag whether to abort the execution queue, if an exception is encountered.
    
    Returns
    -------
    The msg_id of the message sent.


    """
    
    return client.execute(*args, **kwargs)




