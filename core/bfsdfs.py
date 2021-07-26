"""Breadth-first and depth-first search algorithms.
"""
from collections import deque
from core.prog import safeWrapper
from core.utilities import safe_identity_test, NestedFinder

import numpy as np

import nested_lookup as nlu
import dpath

found = deque()
visited = deque()
queued = deque()

def gen_elem(src, ndx):
    if isinstance(src, dict):
        if ndx in src.keys():
            yield src[ndx]
            
    elif NestedFinder.is_namedtuple(src):
        if ndx in src._fields:
            yield getattr(src, ndx)
            
    elif isinstance(src, (tuple, list, deque)):
        if isinstance(ndx, int):
            yield src[ndx]
            
    elif isinstance(src, np.ndarray):
        yield src[ndx]
        
    else:
        yield src
            
            
def gen_nested_value(src, path=None):
    #print("\n\ngen_nested_value src", src, "\npath", path)
    if not path:
        yield src
        
    if isinstance(path, deque): # begins here
        #print("in deque path")
        while len(path):
            pth = path.popleft()
            #print("\tpth", pth)
            yield from gen_nested_value(src, pth)
            
    if isinstance(path, list): # first element is top index, then next nesting level etc
        #print("in list path")
        while len(path):
            ndx = path.pop(0)
            #print("\tndx",ndx, "path", path)
            g = gen_elem(src, ndx)
            #if len(path) == 0:
                #path = None
            try:
                yield from gen_nested_value(next(g), path)
            except StopIteration:
                pass
            
    else:# elementary indexing with POD scalars, ndarray or tuple of ndarray
        yield from gen_elem(src, path)
        #if isinstance(src, dict):
            #print("gen_nested_value in dict src", src, "path", path)
            #if path in src.keys():
                #yield src[path]
            
        #elif NestedFinder.is_namedtuple(src):
            #print("gen_nested_value in namedtuple src", src, "path", path)
            #if path in src._fields:
                #yield getattr(src, path)
                
        #elif isinstance(src, (tuple, list, deque)):
            #print("gen_nested_value in sequence src", src, "path", path)
            #if isinstance(path, int):
                #yield src[path]
            
        #elif isinstance(src, np.ndarray):
            #print("gen_nested_value in ndarray src", src, "path", path)
            #yield src[path]
        
        #else:
            #yield src
            
            
        
    #elif 
    #elif isinstance(src, (tuple, list, deque))
            
    
    

def gen_extract(var, key, index=False):
    if isinstance(var, dict):
        for k, v in var.items():
            if k == key: # if key found in var yield
                yield v
            # else check v (recursive call)
            if isinstance(v, (dict, list, tuple, deque)):
                yield from gen_extract(v, key, index=index)
                
    if isinstance(var, (list, tuple, deque)):
        if index and isinstance(key, int):
            if key < len(var):
                yield var[key]
                
        if isinstance(key, str) and hasattr(var, key): # for named tuples
            yield getattr(var, key) 
            
        for v in var: # no key comparison; key should be an int
            yield from gen_extract(v, key, index=index)
            
def gen_extract_item(var, item, asindex=True):
    if isinstance(var, dict):
        for k, v in var.items():
            visited.append(k)
            if asindex:
                if k == item: 
                    found.append(list(visited))
                    yield v
            else:
                if v == item:
                    found.append(list(visited))
                    yield k
                    
            if isinstance(v, (dict, list, tuple, deque)):
                yield from gen_extract_item(v, item, asindex)
            
            if len(visited):
                visited.pop()
                
        if len(visited):
            visited.pop()
                
    elif isinstance(var, (list, tuple, deque)):
        # search in structs nested here, before going for index
        if asindex:
            if isinstance(item, int) and item < len(var):
                visited.append(item)
                found.append(list(visited))
                yield var[item]
                
            elif isinstance(item, str) and hasattr(var, item): # for named tuples
                visited.append(item)
                found.append(list(visited))
                yield getattr(var, item)
                
        else:
            if item in var:
                ndx = var.index(item)
                visited.append(ndx)
                found.append(list(visited))
                yield ndx
        
        # NOTE:2021-07-23 18:13:50
        # the loop below is exeuted ONLY if 'item' was not found as a valid index
        # the corrolary is that if item is faound as valid index other nexted structs
        # are overlooked - this therefore is a problem.
        for v in var: # no item or value comparison; delegate to elements
            yield from gen_extract_item(v, item, asindex)
            
        if len(visited):
            visited.pop()
        
def gen_extract_key(var, item):
    if isinstance(var, dict):
        for k, v in var.items():
            visited.append(k)
            if k == item: 
                found.append(list(visited))
                yield v
                    
            if isinstance(v, (dict, list, tuple, deque)):
                yield from gen_extract_key(v, item)
            
            if len(visited):
                visited.pop()
                
        if len(visited):
            visited.pop()
                
    elif isinstance(var, (list, tuple, deque)):
        if isinstance(item, int) and item < len(var):
            visited.append(item)
            found.append(list(visited))
            yield var[item]
            
        elif isinstance(item, str) and hasattr(var, item): # for named tuples
            visited.append(item)
            found.append(list(visited))
            yield getattr(var, item)
        
        for k, v in enumerate(var): # no item or value comparison; delegate to elements
            yield from gen_extract_key(v, item)
            
        if len(visited):
            visited.pop()
        
def gen_extract_p(var, item, index=True):
    if isinstance(var, dict):
        #print("in dict, visited:", list(visited))
        for k, v in var.items():
            #print("k", k)
            if index:
                if k == item: # if item found in var yield
                    visited.append(k)
                    #print("in dict, item found as key", k, "=> new visited:", list(visited))
                    found.append(list(visited))
                    #print("\tfound:", list(found))
                    yield v
                    
            elif v == item:
                visited.append(k)
                #print("in dict, item found as value", v, "=> new visited:", list(visited))
                found.append(list(visited))
                #print("\tfound:", list(found))
                yield k
                    
            # no yield at this level: check inside v (recursive call)
            if isinstance(v, (dict, list, tuple, deque)):
                #visited.append(k)
                #print("in dict, check recursive at index", k, "value:", v)
                yield from gen_extract_p(v, item, index=index)
                #if len(visited):
                    #visited.pop()
                
            # no yield: remove k from visited
            if len(visited):
                visited.pop()
                
        if len(visited):
            visited.pop()
                
        #print("in dict, no yields, visited:", list(visited))
                
    elif isinstance(var, (list, tuple, deque)):
        #print("in seq,", list(visited))
        if index:
            if isinstance(item, int) and item < len(var):
                visited.append(item)
                #print("in seq, use item as int index", item, "=> new visited:", list(visited))
                found.append(list(visited))
                #print("\tfound:", list(found))
                yield var[item]
                
            if isinstance(item, str) and hasattr(var, item): # for named tuples
                visited.append(item)
                #print("in seq, use item as name index", item, "=> new visited:", list(visited))
                found.append(list(visited))
                #print("\tfound:", list(found))
                yield getattr(var, item)
                
        if item in var:
            ndx = var.index(item)
            visited.append(ndx)
            #print("in seq, item found as value", item, "=> new visited:", list(visited))
            found.append(list(visited))
            #print("\tfound:", list(found))
            yield ndx
        
        for k, v in enumerate(var): # no item or value comparison; delegate to elements
            #print("in seq enum var", list(visited))
            visited.append(k)
            yield from gen_extract_p(v, item, index=index)
            #if len(visited):
                #visited.pop()
            
        if len(visited):
            visited.pop()
            
        #print("in seq, no yields, visited:", list(visited))
        
def gen_dict_extract(var, key):
    if isinstance(var, dict):
        for k, v in var.items():
            if k == key: # if key found in var yield
                yield v
            # else check v (recursive call)
            if isinstance(v, (dict, list, tuple, deque)):
                yield from gen_dict_extract(v, key)
                
    elif isinstance(var, (list, tuple, deque)):
        for v in var: # no key comparison; key should be an int
            yield from gen_dict_extract(v, key)
            
def gen_dict_extract0(key, var):
    """
    hexerei software
    https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-dictionaries-and-lists
    """
    #if hasattr(var,'iteritems'):
    if hasattr(var,'items'): # python 3
    #try:
        #g = var.items()
    #except AttributeError:
        #pass
    #else:
        #for k, v in g:
        #for k, v in var.iteritems():
        for k, v in var.items(): # python 3
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result

def gen_dict_extract1(key, var): # Alfe
    try:
        g = var.iteritems()
    except AttributeError:
        pass
    else:
        for k, v in g:
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result

def gen_dict_extract2(var, keys):
   for key in keys:
      if hasattr(var, 'items'):
         for k, v in var.items():
            if k == key:
               yield v
            if isinstance(v, dict):
               for result in gen_dict_extract([key], v):
                  yield result
            elif isinstance(v, list):
               for d in v:
                  for result in gen_dict_extract([key], d):
                     yield result    

class Node:
    def __init__(self, key):
        self.data = key
        self.left = None
        self.right = None
        
def height(node):
    if not isinstance(node, None):
        return 0
    
    lheight = height(node.left)
    rheight = height(node.right)
    
    if lheight > rheight:
        return lheight + 1
    
    return rheight + 1

@safeWrapper
def find_leaf(src, leaf, key=True):
    """Search for a leaf object in src - depth-first
    Returns a mixed sequence of hashable objects and int.
    
    Parameters:
    ----------
    
    src: dict, tuple, list
    leaf: object nested deep in src
    
    Example 1:
    
    ar = np.arange(5)
    a = {"a":{"b":[1,2,3], "c":{"d":4, "e":list()}}, "f":{"g":"some text", "h":dict(), "i":ar}}

    find_leaf(a, ar)
    --> ['f', 'i']
     
    find_leaf(a, 2)
    --> ['a', 'b', 1] 
    
    find_leaf(a, 4)
    --> ['a', 'c', 'd']
    
    find_leaf(a, "some text")
    --> ['f', 'g']
    
    """
    path = []
    paths = []
    
    visited = deque()
    queued = deque()
    
    if isinstance(src, dict):
        if hasattr(leaf, "__hash__") and leaf.__hash__ is not None and leaf in src.keys():
            # leaf may be a top level key -> return it
            # keys are by definition unique
            # CAUTION 2021-07-19 14:06:26
            # if src[leaf] is a nested dict and leaf is also found deeper it will
            # be overlooked
            path.append(leaf)
            
        elif any((safe_identity_test(leaf, v) for v in src.values())):
            # leaf may be a top level value
            path += [name for name, val in src.items() if safe_identity_test(val, leaf)]
            
            
        if len(path):
            paths.append(path)
                
        # Now go a dearch for leaf in other branches
        # depth-first search
        for k, v in src.items():
            p = find_leaf(v, leaf)
            if len(p):
                path.append(k)
                path += p
               
    elif isinstance(src, (tuple, list)):
        if any((safe_identity_test(leaf, v) for v in src)):
            path.append(src.index(leaf))
            
        elif isinstance(leaf, str) and hasattr(src, leaf):
            path.append(getattr(src, leaf))
                        
        else:
            # depth first search
            for k, v in enumerate(src):
                p = find_leaf(v, leaf)
                if len(p):
                    path.append(k)
                    path += p
                
    elif safe_identity_test(src, leaf):
        path.append(0)
                    
    return path
                
                
def dict_depth(x):
    """Return max depth of a nested dict
    """
    ret = 0
    depths = list()
    
    dkv = [(k,v) for k,v in x.items() if isinstance(v, dict)]
    
    for kv in dkv:
        dp = dict_depth(kv[1])
        print(kv[0], dp)
        depths.append(dp)
        
    if len(depths):
        ret += 1
        ret += max(depths)
        
    return ret
    
class Finder:
    def __init__(self, src):
        #self.visited = deque(maxlen=len(self.data))
        #self.queued = deque(maxlen=len(self.data))
        self.result = list()
        
        #self.branches = list()
        if isinstance(src, dict):
            self.branches = [[k] for k in src.keys()]
            
        elif isinstance(src, (tuple, list, deque)):
            self.branches = [[k] for k in range(len(src))]
            
        else:
            raise TypeError("src expected to be a dict, tuple, list or collections.deque; got %s instead" % type(src).__name__)
        
        self.data = src

        self.level = 0
        
        print(self.branches)
        
    #def traverse_dict(self, x=None, branch=list()):
        #if x is None:
            #x = self.data
            #self.level = 0
            
        ##if branch is None:
            ##branch = ["/"]
            
        
        ##print("in %s {%s} branch: %s" % ("/".join(["%s"% s for s in branch]), ", ".join(["%s" % k for k in x.keys()]), branch))
        ##print("in branch %s" % branch)
            
        #ret = 0
        #depths = list()
        
        
        #self.level += 1
        
        #for k, (key, val) in enumerate(x.items()):
            #if isinstance(val, dict):
                #self.queued.append([ki for ki in val.keys()])
                #if self.level == 1:
                    #current_branch = self.branches[k]
                #else:
                    
                    
                #current_branch = [k for k in filter(lambda i: i[0:self.level]==[key], self.branches)]
                #print("in branch %s" % branch, "key",key, "current", current_branch, "level", self.level)
                #if len(branch) == 0:
                    #branch.append(key)
                #dp, br = self.traverse_dict(val, current_branch)#, branch+[key])#, branches[k], branches)
                
                #depths.append(dp)
                #if dp > 0: # store in branch
                    #current_branch+=br
                #print("in branch %s" % branch, "key", key, "updated current", current_branch, "level", self.level)
                
        #self.level -= 1
            
        #if len(depths):
            #ret += (max(depths) + 1)
            
        #return ret, branch
    
    def dict_depth(self, x=None, branch=list()):
        if x is None:
            x = self.data
            self.level = 0
            
        #if branch is None:
            #branch = ["/"]
            
        
        #print("in %s {%s} branch: %s" % ("/".join(["%s"% s for s in branch]), ", ".join(["%s" % k for k in x.keys()]), branch))
        #print("in branch %s" % branch)
            
        ret = 0
        depths = list()
        
        dkv = [(k,v) for k,v in x.items() if isinstance(v, dict)]
        
        self.level += 1
        
        #for k, kv in enumerate(dkv):
        for k, (key, val) in enumerate(dkv):
            current_branch = [k for k in filter(lambda i: i[0:self.level]==[key], self.branches)]
            print("in branch %s" % branch, "key",key, "current", current_branch, "level", self.level)
            if len(branch) == 0:
                branch.append(key)
            dp, br = self.dict_depth(val, current_branch)#, branch+[key])#, branches[k], branches)
            
            depths.append(dp)
            if dp > 0: # store in branch
                current_branch+=br
            print("in branch %s" % branch, "key", key, "updated current", current_branch, "level", self.level)
                
        self.level -= 1
            
        if len(depths):
            ret += (max(depths) + 1)
            
        return ret, branch
    
        
    def find(self, data, leaf, key=True):
        """search for a leaf
        
        key = True =>  search for a leaf KEY, return its value: 
            leaf is a (possibly nested) key
            
            CAUTION: the keys are unique at the same nesting level, but not 
            necessarily across different nesting levels
            
        key = False => search for a leaf VALUE, return its tree path:
            leaf is an object, possibly nested => return the path leading to it
            including the KEY it is mapped to
            
        For dict data this is straightforward.
        For sequence data (tuple, list) keys are indices
        
        For nested dict the path looks like:
        [key_0][key_1]...[key_n] for n+1 nesting levels, with key_x being any
        hashable object that can be used as a dict key.
        
        For nested (i.e. ragged) sequences (tuple, lists) the path looks like:
        [ndx_0][ndx_1]...[ndx_n] for n+1 nesting levels, with ndx_x being an int
        
        For nested mixed data (dict containing dict and ragged sequences as above)
        the path reflects the data types (dict/sequence) in the structure;
        the nesting level indicesare always global (i.e. start at 0) so when retrieving
        the path
            
        
        """
        from core.datatypes import reverse_mapping_lookup
        ret = None
        if key: # search for key, return its value(s)
            if isinstance(data, dict):
                if key and leaf in data.keys():
                    ret = data[leaf]
                elif leaf in data.values():
                    ret = reverse_mapping_lookup(data, leaf)
            
        #self.visited.append(leaf)
        #self.queued.append(leaf)
        #while len(self.queued):
            #m = self.queued.popleft()
            
            #if m is leaf:
                #self.result.append(m)
