@echo off
REM Set up \Microsoft Visual Studio 2015, where <arch> is amd64, x86, etc.
rem  ONLY IF NOT USING MSYS2/MinGW-w64
rem  EDIT THE LOCATION OF THE vcvarsall.bat SCRIPT, BELOW
CALL "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64
rem  SET "PROMPT=(x64) $P$G"
rem  EDIT THE LOCATION OF THE scipyenv VIRTUAL ENVIRONMENT, BELOW (LEAVE Scripts\activate AS IS)
CALL "F:\Users\Public\scipyenv\Scripts\activate" 
rem  Use the line below if scipyenv environment was created with msys2/mingw64
REM echo "NOTE: For access to the MinGW-w64 toolchain call 'scipyact' from MinGW-w64 shell"
REM "F:\Users\Public\scipyenv-mingw64\bin\activate"
set INCLUDE=%VIRTUAL_ENV%\include;%INCLUDE%
set LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%LIB%
set LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%LIBPATH%
set PATH=%VIRTUAL_ENV%\bin;%PATH%
SET "PROMPT=(x64 scipyenv) $P$G"
echo on
