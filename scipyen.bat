@echo off
set scipyendir=E:\scipyen
call E:\scipyenv\Scripts\activate
set "SDK=e:\scipyen_sdk"
set "LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%VIRTUAL_ENV%\lib\site-packages\vigra;%SDK%\lib;%SDK%\lib64;%LIB%"
set "LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib\site-packages\vigra;%VIRTUAL_ENV%\lib64;%SDK%\lib;%SDK%\lib64;%LIB%"
set "INCLUDE=%VIRTUAL_ENV%\include;%SDK%\include;%INCLUDE%"
set "PATH=%VIRTUAL_ENV%\bin;%VIRTUAL_ENV%\Scripts;%SDK%\bin;%PATH%"
set "PYTHONSTARTUP=%SDK%\scipyen_startup_win.py"
echo "Using Python Virtual Environment in %VIRTUAL_ENV%"
cmd /C "python %scipyendir%\scipyen.py"
