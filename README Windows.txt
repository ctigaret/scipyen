Before using Scipyen you musy create a virtual environmment, following the steps below:

0. install github cli, authorise youself with scipyen's github, then choose a suitable location (e.g. c: drive)
you will need ~ 5-8 GiB free disk space to contain the environment, then clone the scipyen repository.

NOTE: since you;re already reading this I assume you have already perfomred this step

You also want to clone the scipyen_plugins repository

ATTENTION as a general rule, MAKE SURE YOU AVOID long file names and filenames with spaces or containing any
other characters than 'a' to 'z', 'A' to 'Z', '0' to '9' and '_' (underscore) or '-' (dash) in them.

1. install miniforge3 (for ALL users).

For example, to install the latest release as of 2026-06-02 12:52:14:
• go to https://github.com/conda-forge/miniforge/releases/tag/26.3.2-3
• download the Windows installer
https://github.com/conda-forge/miniforge/releases/download/26.3.2-3/Miniforge3-26.3.2-3-Windows-x86_64.exe
• run the installer
• open the newly created miniforge prompt and run

    conda init

mamba shell init --shell cmd.exe

2. install uv (for ALL users)

• go to https://docs.astral.sh/uv/ and navigate to "Installation"; follow their instructions, but in a nutshell:

    ∘ open a powershell window
    ∘ execute the following command:

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"



3. open an administator command prompt, go to your LOCAL respository (i.e. THIS directory) and run

mamba_create_env_windows.bat. Again, here you need some good disk space (see step 0); CAUTION When prompted,
you may have to pass a location different from the default of "c:\scipyenv", but MAKE SURE it is not the same
as this git repository!

WARNING: any further changes to this environment MUST be made from an administrator prompt

