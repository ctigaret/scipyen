# Welcome to Scipyen

Scipyen (**Sci**entific **py**thon **e**nvironment for **n**euroscience) is an
open-source environment for the analysis of electrophysiology and 
microscopy imaging data using Python programming language. 

Scipyen provides a framework similar to an Integrated 
Development Environment (IDE)[^1], where the user creates their own data 
analysis workflows or pipelines according to their need. Instead of offering a preset collection of analysis scenarios[^2], Scipyen integrates
third party numerical analysis software, a set of GUI tools for the visualization
of electrophysiology[^3], microscopy[^4], and tabular[^5] data, and provides a mechanism to run your own Python scripts[^6].

THIS SOFTWARE IS PROVIDED AS IS AND WITHOUT ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTIES OF MERCHANTIBILITY AND FITNESS FOR A PARTICULAR PURPOSE.

## Main features
* [Graphical User Interface](https://en.wikipedia.org/wiki/Graphical_user_interface)[(GUI)](#Scipyen_screenshot) with 
    - read-only[^7] access to the file system
    - a dynamic view into the workspace variables[^8]
    - a command history viewer[^9]
    - viewers for data objects
    - script manager[^10]
* A Python console[^11]
* Possibility to run external python processes via an "External console", and also accessible via [jupyter notebooks](https://jupyter.org/)).
* A system for data plotting (via [matplotlib](https://matplotlib.org/), [seaborn](https://seaborn.pydata.org/), [pyqtgraph](https://www.pyqtgraph.org/)) that can be extended to use other libraries[^12].
* A script manager[^13] for user-written Python code[^6].

## <a name=use_virtual_environment></a>Getting started
Scipyen should be used inside a [virtual Python environment](https://www.google.com/search?q=virtual+python+environment) which allows the local installation of 3<sup>rd</sup> party Python packages without interfering with the host computer. 

Before using Scipyen, follow these steps:

1. Clone the Scipyenv repository:
    ```
    git clone github.com/ctigaret/scipyen.git
    ```
2. Create a virtual python environment.

        
    2.1 In a terminal window navigate to the top directory of the cloned repository
    and launch the environment installation script (NOTE: I assume you cloned
    scipyen in your home directory; make sure you adjust the paths correctly):
        
    * Linux:
        
    ```bash
    cd ~/scipyen
    sh ./env_install.sh
    ```
    
    * MacOS:
        
    ```bash
    cd ~/scipyen
    sh ./mamba_env_install_macos.sh
    ```
    
    * Windows
    
    ```dos
    cd c:\users\<my user name>\scipyen
    mamba_env_install_windows.bat
    ```

3. Launch Scipyen:
    
    3.1. Linux/MacOS:
        
    * The environment installation script creates an executable shell script ~/bin/scipyen.
    Make sure ~/bin is in your PATH environment variable then call this script in a terminal window.
    
    * To activate the virtual environment in order to change/upgrade installed python packages, 
    call the command "scipyact" in a terminal window (NOTE: This is sourced from the file "~/.scipyenrc"
    created by the environment installation script).
    
    * To launch scipyen manually, in a terminal window activate the environment as above, 
    navigate to the source directory inside the local git repository, e.g.
    ```bash
    cd ~/scipyen/src/scipyen 
    ```
    
    then launch Scipyen with:
    
    ```bash
    python scipyen.py
    ```
    
    3.2 Windows:
        
    * Use the desktop shortcut that was created by the environment installation script.


## Author:
Cezar M. Tigaret <cezar.tigaret@gmail.com>, <tigaretc@cardiff.ac.uk>

Distributed under [GNU General Public License v.3.0 (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.en.html)


<a name=Scipyen_screenshot> ![Scipyen Screenshot](doc/ScipyenScreenshot1.png)</a>
Scipyen session with:

1. The main window, with workspace viewer ("User variables"), file system viewer and command history.
2. The console
3. The script manager
4. Dictionary viewer (DataViewer_0)
5. Electrophysiology data viewer (SignalViewer_0)



* * * 

[^1]: See [Spyder](https://www.spyder-ide.org/) for a comprehensive scientific python environment
and [Eric](https://www.spyder-ide.org/) for Python programming with a wider purpose.
Also, see [GNU Octave](https://octave.org/), [Scilab](https://www.scilab.org/),
[Matlab](https://www.mathworks.com/products/matlab.html) 
and [Sage](https://www.sagemath.org/) for scientific programming environments 'outside' the Python universe.

[^2]: Scipyen does contain some example analyses workflows e.g. for mEPSC analysis, action potential analysis, LTP, and two-photon line scanning 
for fluorescence Ca^2+^ imaging. These workflows are specific to the author's lab environment and they are in continuous development.

[^3]: Electrophysiology data is represented using [NeuralEnsemble](https://github.com/NeuralEnsemble)'s python [neo](https://github.com/NeuralEnsemble/python-neo) package.

[^4]: For for a more extensive, open source, software for image analysis see, for example, [ImageJ/Fiji](https://fiji.sc/) .

[^5]: DataFrame objects from Python [pandas package](https://pandas.pydata.org/) and matrices.

[^6]: Scipyen's author tries hard to avoid [re-inventing the wheel](https://en.wikipedia.org/wiki/Reinventing_the_wheel), therefore Scipyen **does not provide a code editor** for Python. While *any* text editor can be used, there are several powerful open source editors [available](https://en.wikipedia.org/wiki/List_of_text_editors) e.g., [Kate](https://kate-editor.org/), [vim](https://www.vim.org/), [GNU Emacs](https://www.gnu.org/software/emacs/), [NEdit (the Nirvana Editor)](https://sourceforge.net/projects/nedit/files/nedit-source/), [Atom](https://github.com/atom/atom), to name just a few.

[^7]: This is by design. Following the principle of [not reinventing the wheel](https://en.wikipedia.org/wiki/Reinventing_the_wheel)[^6], Scipyen has no functionality to create/delete files and directories, apart from reading/writing data objects to the disk. Scipyen is intended to be used in a [Desktop environment](https://en.wikipedia.org/wiki/Desktop_environment) with [tools](https://en.wikipedia.org/wiki/File_manager) to navigate and modify the file system, and gives the possibility to open the current working directory in a desktop [tool](https://en.wikipedia.org/wiki/File_manager) via a context menu.

[^8]: Provides access to variables created during a session, including instances of data type-specific viewers, and updates itself whenever variables are created, modified, or removed. The items in the viewer are actionable via a context menu.

[^9]: Commands are grouped by session, and can be replayed by double clicking, dragging into the console, or copy then pasted in a text editor to create scripts.

[^10]: The Script manager simply provides a convenience to collect python scripts so they are readily available across sessions. 

[^11]: Scipyen's console is based on [jupyter qtconsole](https://qtconsole.readthedocs.io/en/stable/index.html), and gives access to the "user workspace"[^7] and various modules (either part of Scipyen, or installed in your Python environment). To keep things "clean", the workspace viewer shows *only* the variables created since the start of the session.

[^12]: For more extensive data plotting applications see [Veusz](https://veusz.github.io/), [SciDaVis](https://scidavis.sourceforge.net/), [LabPlot2](https://labplot.kde.org/), [XmGrace](https://plasma-gate.weizmann.ac.il/Grace/), and not least the venerable [GNU Plot](http://www.gnuplot.info/), in addition to a galaxy of [Python-based data visualization frameworks](https://www.google.com/search?q=data+visualization+in+python). Python-based visualization frameworks can be used from within Scipyen's console as long as they provide modules and extensions available to Scipyen's python environment (this typcially required their installation (*inside* the environment in which Scipyen is used).

[^13]: The scripts are written in Python language and can be located anywhere in the file system. They typically are meant to be used within a Scipyen session, and therefore may depend on modules and packages installed inside the virtual Python environment where Scipyen runs. Some scripts may use modules already loaded (or imported) in a Scipyen session, and available at the Scipyen console. Therefore, such scripts are **not guaranteed** to run in an independent Python session, although they can be written to enable this.








