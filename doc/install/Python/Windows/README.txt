###############################################################################                                                                      
#               Copyright (C) 2021 Cezar M. Tigaret                
#                                                                       
#  This program is free software: you can redistribute it and/or modify 
#  it under the terms of the GNU General Public License as published by 
#  the Free Software Foundation, either version 3 of the License, or    
#  (at your option) any later version.                                  
#                                                                       
#  This program is distributed in the hope that it will be useful,      
#  but WITHOUT ANY WARRANTY; without even the implied warranty of       
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        
#  GNU General Public License for more details.                         
#                                                                       
#  You should have received a copy of the GNU General Public License    
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#                                                                       
#                                                                       
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND    
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES   
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND          
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT       
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,      
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING      
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR     
#     OTHER DEALINGS IN THE SOFTWARE.                                   
###############################################################################

NOTE: These instructions are for creating a Python virtual environment under Windows
for running Scipyen.

You MUST create a virtual python environment specific for the version of Python
you are planning to use, for the following reasons:
    1. everything else that relies on the specifc Python version can properly 
    locate what it needs, without interference from the system's default Python
    interpreter
    2. Any Python packages installed specifically for the Python version using 
    the version-specifc 'pip' tool will not interfere (or worse, ovderwrite)
    system-wide packages

================================================================================
1. INSTALL PYTHON - below, the Python stack from Python.org will be used
================================================================================
Grab the installer from Python.org (for now, use Python 3.9.7), run it and
choose to install "for everyone"; make sure to activate "Disable limit on PATH" 
or whatever the option is to this effect.

================================================================================
2. CREATE A VIRTUAL PYTHON ENVIRONMENT
================================================================================

After installing Python (e.g., 3.9.7, see above) in a (regular) command prompt
run:

pip install virtualenv

Then:

1) cd into a drive:\directory_path WITHOUT SPACES IN THE PATH NAME 

2) run virtualenv <your_preferred_environment_name> e.g.:
    
    virtualenv scipyen
    
NOTE: This will create the environment's ROOT directory that will be referred to
as VIRTUAL_ENV:

    drive:\directory_path\scipyenv
    
(e.g., e:\users\user\scipyenv )
    
================================================================================
3. VIRTUAL PYTHON ENVIRONMENT ACTIVATION SCRIPTS:
================================================================================

3.1. Create a Scripts directory in your Windows home directory (%USERPROFILE%)

3.2. Add to your %PATH% PERMANENTLY:

	%USERPROFILE%\Scripts
	

(NOTE: use Windows settings, search for "environment", select 
"Edit environment variables for your account" -> in the new dialog edit %PATH% ->
"add" %USERPROFILE%\Scripts)

* restart the command prompt

3.3. Copy scipyen_startup.py to %VIRTUAL_ENV%\Scripts

3.4. copy scipyact.bat, vs64.bat and scipyact_vs64.bat to %USERPROFILE%\Scripts

(NOTE: you can name these scripts whatever you like, just make note of what each
does; in the following, I will use the above names by convention)

3.4.1. Scripts usage:
    scipyact.bat => activates the virtual python environment 
                    USE THIS FOR REGULAR USE OF Scipyen, inside the virtual 
                    python environment
        
    vs64.bat => activates Visual Studio 2019 development environment 
                use for building software INDEPENDENTlLY OF the virtual python 
                environment
        
    scipyact_vs64.bat => activates BOTH the python virtual environment AND the
                         Visual Studio 2019 development environment
                         use for building Scipyen's dependencies INSIDE the 
                         virtual python environment (RECOMMENDED)
        
    



