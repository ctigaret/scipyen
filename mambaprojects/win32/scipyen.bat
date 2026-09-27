@echo off
activate C:\scipyenv && (

set QT_API=pyqt6
set PYQTGRAPH_QT_LIB=PyQt6
set FORCE_QT_API=1

python -Xfrozen_modules=off C:\scipyen\src\scipyen\scipyen.py

)
