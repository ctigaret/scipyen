# Welcome to Scipyen

Scipyen (**Sci**entific **py**thon **e**nvironment for **n**euroscience) is an
open-source environment for the analysis of electrophysiology and 
microscopy imaging data using Python programming language. 

Scipyen provides a framework similar to an Integrated 
Development Environment (IDE)[<sup>1</sup>](#NOTE_1), where the user creates their own data 
analysis workflows or pipelines according to their need. 

Instead of offering a preset collection of analysis scenarios[<sup>2</sup>](#NOTE_2), Scipyen integrates
third party numerical analysis software, a set of GUI tools for the visualization
of electrophysiology[<sup>3</sup>](#NOTE_3), microscopy[<sup>4</sup>](#NOTE_4), and tabular[<sup>5</sup>](#NOTE_5) data, and a
mechanism to run your own Python scripts.

## Main features
* [Graphical User Interface](https://en.wikipedia.org/wiki/Graphical_user_interface)[(GUI)](#Scipyen_screenshot) with 
    - read-only[<sup>6</sup>](#NOTE_6) access to the file system
    - a dynamic view into the workspace variables[<sup>7</sup>](#NOTE_7)
    - a command history viewer[<sup>8</sup>](#NOTE_8)
    - viewers for data objects
    - script manager[<sup>9</sup>](#Note_9)
* A Python console[<sup>10</sup>](#NOTE_10)
* Interaction with external python processes (including [jupyter notebooks](https://jupyter.org/)) via an "External console"
* A system for data plotting (via [matplotlib](https://matplotlib.org/), [seaborn](https://seaborn.pydata.org/), [pyqtgraph](https://www.pyqtgraph.org/)) which can be extended[<sup>11</sup>](#NOTE_11).
* A script manager[<sup>12</sup>](#NOTE_12) for user-written Python code[<sup>13</sup>](#NOTE_13)

## <a name=use_virtual_environment></a>Getting started
Scipyen should be used inside a [virtual Python environment](https://www.google.com/search?q=virtual+python+environment) which allows the local installation of 3<sup>rd</sup> party Python packages without interfering with the host computer. 

Before using Scipyen, you need to create a virtual python environment, see [`doc/install/INSTALL.md`](doc/install/INSTALL.md) for details.

Then clone this repository then simply run the `scipyen.py` script located
in the top `scipyen` directory, e.g.:
```python
python ~/scipyen/scipyen.py
```

The following 3<sup>rd</sup> party libraries are **necessary**:

* python-neo - for electrophysiology data
* vigra - for image analysis and processing, and image I/O
* pyqt5 - for the GUI
* pyqtgraph - for the GUI
* jupyter and jupyer qtconsole - for the GUI console


<a name=Scipyen_screenshot> ![Scipyen Screenshot](doc/ScipyenScreenshot1.png)</a>
Scipyen session with:

1. The main window, with workspace viewer ("User variables"), file system viewer and command history.
2. The console
3. The script manager
4. Dictionary viewer (DataViewer_0)
5. Electrophysiology data viewer (SignalViewer_0)

* * * 
###### Footnotes:
<a name=NOTE_1></>[1]: See [Spyder](https://www.spyder-ide.org/) for a comprehensive scientific python environment
and [Eric](https://www.spyder-ide.org/) for Python programming with a wider purpose.
Also, see [GNU Octave](https://octave.org/), [Scilab](https://www.scilab.org/),
[Matlab](https://www.mathworks.com/products/matlab.html) 
and [Sage](https://www.sagemath.org/) for scientific programming environments 'outside' the Python universe.

<a name=NOTE_2></>[2]: Scipyen does contain some example analyses forkflows e.g. 
for mEPSC analysis, action potential analysis, LTP, and two-photon line scanning 
for fluorescence Ca^2+^ imaging. These workflows are specific to the author's lab 
environment and they are in continuous development.

<a name=NOTE_3></>[3]: Electrophysiology data is represented using [NeuralEnsemble](https://github.com/NeuralEnsemble)'s python [neo](https://github.com/NeuralEnsemble/python-neo) package.

<a name=NOTE_4></>[4]: For for a more extensive,
open source, software for image analysis see, for example, [ImageJ/Fiji](https://fiji.sc/) .

<a name=NOTE_5></>[5]: DataFrame objects from Python [pandas](https://pandas.pydata.org/) package and Matrices.

<a name=NOTE_6></>[6]: This is by design. Scipyen's author tries hard to avoid 
[re-inventing the wheel](https://en.wikipedia.org/wiki/Reinventing_the_wheel), and therefore Scipyen has no functionality to create/delete files and directories, other than saving data objects to the disk. Scipyen is intended to be used in a [Desktop 
environment](https://en.wikipedia.org/wiki/Desktop_environment) with [tools](https://en.wikipedia.org/wiki/File_manager) to navigate and modify the file system, and gives the possibility to open the current working directory in
a desktop [tool](https://en.wikipedia.org/wiki/File_manager) via a context menu.

<a name=NOTE_7></>[7]: Provides access to variables created during a session, including
instances of data type-specific viewers, and updates itself whenever variables are
created, modified, or removed. The items in the viewer are actionable via a context menu.

<a name=NOTE_8></>[8]: Commands are grouped by session, and can be replayed by double clicking, dragging into the console, or copy/pasted in a text editor to create scripts.

<a name=NOTE_9></>[9]: Scipyen does not provide its own script editor, but script can be edited in any suitable editor

<a name=NOTE_10></>[10]: Scipyen's console is based on [jupyter qtconsole](https://qtconsole.readthedocs.io/en/stable/index.html), and gives access to the "user workspace"[<sup>7</sup>](#NOTE_7) and various modules (either part of Scipyen, or installed in your Python environment). To keep things "clean", the workspace viewer shows *only* the variables created since the start of the session.

<a name=NOTE_11></>[11]: For more extensive data plotting applications see [Veusz](https://veusz.github.io/), [SciDaVis](https://scidavis.sourceforge.net/), [LabPlot2](https://labplot.kde.org/), [XmGrace](https://plasma-gate.weizmann.ac.il/Grace/), and not least the venerable [GNU Plot](http://www.gnuplot.info/), in addition to a galaxy of [Python-based data visualization frameworks](https://www.google.com/search?q=data+visualization+in+python). Python-based visualization frameworks can be used from within Scipyen's console as long as they provide modules and extensions available to Scipyen's python environment (this typcially required their installation (sinside* the environment in which Scuipyen is used).

<a name=NOTE_12></>[12]: The Script manager offers a flexible collection of python scripts to be readily available across sessions. Following the principle of [not reinventing the wheel](https://en.wikipedia.org/wiki/Reinventing_the_wheel)[<sup>6</sup>](#NOTE_6), Scipyen **does not provide a code editor** for Python. While *any* text editor can be used, there are several powerful open source editors [available](https://en.wikipedia.org/wiki/List_of_text_editors) e.g., [Kate](https://kate-editor.org/), [vim](https://www.vim.org/), [GNU Emacs](https://www.gnu.org/software/emacs/), [NEdit (the Nirvana Editor)](https://sourceforge.net/projects/nedit/files/nedit-source/), [Atom](https://github.com/atom/atom), to name just a few.

<a name=NOTE_13></>[13]: The scripts are written in Python language and can be located anywhere in the file system. They typically are meant to be used within a Scipyen session, and therefore may depend on modules and packages installed inside the virtual Python environment where Scipyen runs. Some scripts may use modules already loaded (or imported) in a Scipyen session, and available at the Scipyen console. Therefore, such scripts are **not guaranteed** to run in an independent Python session, although they can be written to enable this.








