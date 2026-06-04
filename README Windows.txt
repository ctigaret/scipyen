CHANGELOG:

2026-06-03 13:01:20

use minforge to create an environment for your OWN use

Before using Scipyen you must create a virtual environmment, following the steps below:

0. install github cli, authorise youself with scipyen's github, then choose a suitable location (e.g. c: drive)
you will need ~ 5-8 GiB free disk space to contain the environment, then clone the scipyen repository.

NOTE: since you're already reading this I assume you have already perfomred this step

You also want to clone the scipyen_plugins repository

ATTENTION as a general rule, MAKE SURE YOU AVOID long file names and filenames with spaces or containing any
other characters than 'a' to 'z', 'A' to 'Z', '0' to '9' and '_' (underscore) or '-' (dash) in them.

1. install miniforge3 (for current user).

For example, to install the latest release as of 2026-06-02 12:52:14:
• go to https://github.com/conda-forge/miniforge/releases/tag/26.3.2-3
• download the Windows installer https://github.com/conda-forge/miniforge/releases/download/26.3.2-3/Miniforge3-26.3.2-3-Windows-x86_64.exe
• run the installer
• open the newly created miniforge prompt and run

    conda init



2. install uv (for ALL users)

• go to https://docs.astral.sh/uv/ and navigate to "Installation"; follow their instructions, but in a nutshell:

    ∘ open a powershell window
    ∘ execute the following command:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"



3. open the command prompt, go to your LOCAL respository (i.e. THIS directory) and run

mamba create -n scipyenv --file mambaprojects\win32\scipyenv.yml

4. activate the new environment -- AS A RULE OF THUMB ALWAYS CALL activate scipyenv; you ONLY need to call mamba activate sciopyenv if you are NOT running inside a Miniforge prompt

mamba activate scipyenv

5. reconfigure jupyter runtime dir for current session:

set JUPYTER_RUNTIME_DIR=%USERPROFILE%\.local\share\jupyter

5.1 also do this permanently in Windows setings dialog (by hand ⌢ )
    -> restart the shell then run the following commands to confirm that Qtconsole works

    activate scipyenv

    jupyter qtconsole


From here onwards, all commands must be run with scipyen environment activated.

Unfortunately, this means you will have to execute them manually and inspect the
output for any errors and BEFORE answering the (Y/n) prompt; when necessary, try
to manually solve any issues that arise (if there weren't any, all these packages
would have been inclued in the ``dependencies`` section of the ``scipyenv.yml``
environment specification file above ⌢ ...)

NOTE: Not sure --use-uv is of any use


6. generate qtconsole configuration # =>  ~\.jupyter\jupyter_qtconsole_config.py

jupyter qtconsole --generate-config

7. install additional stuff

7.1 matplotlib -- needs to be done via pip as the conda-forge packages depend on pyside6 and messes up pyqt6

uv pip instal matplotlib


7.2: call mamba --use-uv --yes install --file mamba-conda-forge-packages.txt

7.3 call uv pip install -r mamba-pip-packages.txt

7.4 install Kepler console themes

cd c:/scipyen/src/scipyen/gui/scipyen_console_styles/
uv pip install --no-deps .

8. NOW is a good time to test scipyen

set QT_API=pyqt6

python -Xfrozen_modules=off c:\scipyen\src\scipyen\scipyen.py


# -- OBSOLETE ------------------------------------------------------------------------------------------------ #
7.2 vigra, also pulls fftw, glpk, hdf5, imath, libboost, openexr, openjph, vs2015_runtime

mamba install --use-uv vigra

7.3 mamba install --use-uv jupyterthemes jupyter_qtconsole_colorschemes

7.4 pyqtgraph
mamba install --use-uv pyqtgraph

7.8 treelib
mamba install --use-uv treelib

7.9 pyxdg

mamba install --use-uv pyxdg

7.10 ipyparallel, also pulls tqdm
mamba install --use-uv ipyparallel

7.11 pywavelets
mamba install --use-uv pywavelets

7.12 qimage2ndarray
mamba install --use-uv qimage2ndarray

7.13 sympy
mamba install --use-uv sympy

7.14 scipy
mamba install --use-uv scipy

7.15 python-neo, also pulls quantities
mamba install --use-uv python-neo

7.16 cmocean, also pulls colorspacious
mamba install --use-uv cmocean

7.17 pandas
mamba install --use-uv pandas

7.18 pandas-flavor, also pulls xarray
mamba install --use-uv pandas-flavor

7.19 pyserial
mamba install --use-uv pyserial

7.20 termcolor2, alao pulls termcolor
mamba install --use-uv termcolor2

7.21 pyinstaller, also pulls altgraph, future, pefile, pyinstaller-hooks-contrib, pywin32-ctypes
mamba install --use-uv pyinstaller

7.22 opencv, also pulls other packages including libusb, and py-opencv
mamba install --use-uv opencv

7.23 shapely, also pulls geos
mamba install --use-uv shapely

7.24 seaborn, also pulls patsy, statsmodels, and (IF NOT ALREADY PRESENT) scipy, pandas
mamba install --use-uv seaborn

7.25 pingouin, also pulls scikit-learn
mamba install --use-uv pingouin

7.26 scikit-image
mamba install --use-uv scikit-image

7.27 scikit-bio, also pulls h5py
mamba install --use-uv scikit-bio

7.28 inflect, also pulls more-itertools (overwrites the pip one, above)
mamba install --use-uv inflect

7.29 dill
mamba install --use-uv dill

7.30 pynwb
mamba install --use-uv pynwb

7.31 sphinx, also pulls docutils, imagesize, sphinxcontrib-* among others (and maybe pygments but they shold already be there since jupyter)
mamba install --use-uv sphinx

7.32 markdown
mamba install --use-uv markdown

7.33 docrepr
mamba install --use-uv docrepr

7.34 restructuredtext_lint
mamba install --use-uv restructuredtext_lint

7.34 marko
mamba install --use-uv marko

7.35 meshio, also pulls cftime, hdf4 importlib_metadata, netcdf4, rich, mdurl, markdown-it-py
mamba install --use-uv meshio

7.36 jupyterthemes jupyter_qtconsole_colorschemes
mamba install --use-uv jupyterthemes jupyter_qtconsole_colorschemes

7.37 ancillaries the following need installed invidiually by calling uv pip install <package>

confuse, isodate, drawsvg

tribool, pyabf, hdf5view, imreg-dft,

modelspec (also pulls cattrs, dnspython, docstring-parser, pymongo

python-magic

winshell

openmath (also pulls lxml)

openexpressions

entrez-utils

taxoniq (also pulls marisa-trie, ncbi-refseq-*, ncbi-taxon-db)

nbci-taxonomist (also pulls entrezpy)

nixio

8. NOW is a good time to test scipyen

set QT_API=pyqt6

python -Xfrozen_modules=off c:\scipyen\src\scipyen\scipyen.py

8. install Kepler console themes


cd c:/scipyen/src/scipyen/gui/scipyen_console_styles/
uv pip install --no-deps .

