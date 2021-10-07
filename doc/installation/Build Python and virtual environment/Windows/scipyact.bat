@echo off
rem  EDIT THE LOCATION OF THE scipyenv VIRTUAL ENVIRONMENT, BELOW (LEAVE Scripts\activate AS IS)
CALL "F:\Users\Public\scipyenv\Scripts\activate" 
set LIB=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%LIB%
set LIBPATH=%VIRTUAL_ENV%\lib;%VIRTUAL_ENV%\lib64;%LIBPATH%
set PATH=%VIRTUAL_ENV%\bin;%PATH%
echo on
