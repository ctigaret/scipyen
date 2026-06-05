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

NOTE: Can also install for all users

• For example, to install the latest release as of 2026-06-02 12:52:14:
    go to https://github.com/conda-forge/miniforge/releases/tag/26.3.2-3
• download the Windows installer https://github.com/conda-forge/miniforge/releases/download/26.3.2-3/Miniforge3-26.3.2-3-Windows-x86_64.exe
• run the installer

• ATTENTION, MANDATORY:
    open the newly created miniforge prompt and run

    conda init



2. install uv (for ALL users)

• go to https://docs.astral.sh/uv/ and navigate to "Installation"; follow their instructions, but in a nutshell:

    ∘ open a powershell window
    ∘ execute the following command:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"



3. Create the environment - AVOID USING SPACES in file names; keep it simple, and
use only characters in the range [a-z, A-Z, 0-9, - _] (i.e., letters, digits, dash and underscore
only, and no other fancy or unicode stuff...)

NOTE: if miniforge was installed for all users, then to create an environment
for yourself, you must create a file named ".condarc" in your user directory
(home directory) containing the following two lines:

pkgs_dirs:
 - ~\.conda\pkgs

then quit the miniforge prompt

Assuming that scipye git repository was cloned as c:\scipyen:

Open a miniforge promp

a) if miniforge was installed for yourself:
mamba --use-uv --yes create -n scipyenv --file mambaprojects\win32\scipyenv.yml

b) if miniforge was installed for ALL users:

mamba --use-uv --yes create -prefix c:\scipyenv --file c:\scipyen\mambaprojects\win32\scipyenv.yml

4. activate the new environment -- AS A RULE OF THUMB ALWAYS CALL activate scipyenv;
you ONLY need to call mamba activate scipyenv if you are NOT running inside a
Miniforge prompt.

WARNING: depending on how miniforge was installed you may need to run miniforge
as administrator from now on.

a) if installed for yourself:
mamba activate scipyenv

b) if installed for all users:
mamba activate c:\scipyenv

5. reconfigure jupyter runtime dir for current session:

set JUPYTER_RUNTIME_DIR=%USERPROFILE%\.local\share\jupyter

5.1 also do this permanently in Windows setings dialog (by hand ⌢ )
    -> restart the shell then run the following commands to confirm that QtConsole works

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

7. install required packages

7.1 matplotlib -- needs to be done via pip as the conda-forge packages depend on pyside6 and messes up pyqt6

uv pip install matplotlib

7.2: call mamba --use-uv --yes install --file c:\scipyen\mambaprojects\win32\mamba-conda-forge-packages.txt

7.3 call uv pip install -r c:\scipyen\mambaprojects\win32\mamba-pip-packages.txt

7.4 install Kepler console themes

cd c:/scipyen/src/scipyen/gui/scipyen_console_styles/
uv pip install --no-deps .

8. NOW is a good time to test scipyen

set QT_API=pyqt6

python -Xfrozen_modules=off c:\scipyen\src\scipyen\scipyen.py

9. make a batch file (assuming you have run ``conda init`` earlier)
with the following contents (MAKE SURE TO ADAPT paths to your own installation:

echo off
activate C:\scipyenv && (

set QT_API=pyqt6
set PYQTGRAPH_QT_LIB=PyQt6
set FORCE_QT_API=1

python -Xfrozen_modules=off C:\scipyen\src\scipyen\scipyen.py

)

Save this as scipyen.bat somewhere in your OWN PATH environment variable.
I prefer to place is in <home>\Scripts, and add this folder to your PATH
environment valriable (using the Windows Settings app)

.


