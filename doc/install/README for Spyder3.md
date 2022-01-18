**Created:** on Sun Oct  6 21:11:29 2019

**Author:** Cezar M. Tigaret *TigaretC@cardiff.ac.uk*


# Running scipyan in Spyder 3

At the moment, scypien can be run in spyder3 as a separate process.

This is equivalent to running pict.py from the scypian directory, in a shell: it simply
starts a separate python3 process, with its own PyQt5 event loop, embedded
IPython kernel and namespace (user workspace). 

The downside is that none of the variables created in the application are available to spyder.
Also none of the modules (and their contents) will be available to spyder, unless manually
imported and their dependencies resolved, so editing the code will require restarting
scipyan.

So in this paradigm spyder's role is no more than that of a text editor with python
syntax highlighting (one could use Kate for this).


1. Import scipyan as a project in spyder3:
        
- Menu "Projects" -> "New Project".
     - In the new project dialog:
          * choose "Existing directory"
                
          * select the location of scypian, e.g.:
> /home/cezar/scipyan
                    
          * select project type: "Empty project" 
                    from the drop-down combo box
    
2. Open the project (if project already created) by 
            selecting its location, e.g.:
> /home/cezar/scypien
        
3. Open pict.py in spyder editor
        
4. Menu "Run" -> "Run"
        
**NOTE:** When running for the first time,
               the "Run configuration per file" dialog shows up:

- Choose "Execute in an external system terminal"

5. On subsequent runs: just select "Run" from the "Run" menu; 

    * for other options, select "Configuration per file" from the "Run" menu.

##TODO

- Better integration of scipyan with spyder i.e, "Execute in current console" -- contemplate:
    - find out from pict code whether we're running inside spyder (in the main clause?)
    - if run like this, then avoid creating a new PyQt event loop?
    - if run from within spyder, then replace pict kernel with spyder kernel (get_ipython())
    - use spyder's kernel namespace as pict's workspace
    - no ScipyenWindow
    - what about the other imports?

    The advantage would be that variables created in scipyan will be available to spyder3;
    individual modules in scipyan might be directly imported into spyder3 and therefore
    used directly with your data (i.e., spiyder3 takes over the role of ScipyenWindow).
    One shoudl still be able to use sub-packages of scipyan (e.g. modules in core, gui, etc)
        
