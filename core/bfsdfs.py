"""Breadth-first and depth-first search algorithms.
"""
from collections import deque
from prog import safeWrapper
from core.utilities import safe_identity_test

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
def find_leaf(src, leaf):
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
                
    
class Finder:
    def __init__(self, src):
        self.data = src
        self.visited = deque()
        self.queued = deque()
        self.result = list()
        
    def fs(self, data, leaf):
        self.visited.append(leaf)
        self.queued.append(leaf)
        while len(self.queued):
            m = self.queued.popleft()
            
            if m is leaf:
                self.result.append(m)
