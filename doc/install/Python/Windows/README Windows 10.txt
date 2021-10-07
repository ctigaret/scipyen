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

NOTE: This is for creating a Python virtual environment under Windows, used for
running Scipyen

Grab the installer from Python.org (for now, use Python 3.9.7), install "for everyone" and make
sure to activate "Disable limit on PATH" or whatever the option is to this effect.

================================================================================
CREATE A VIRTUAL PYTHON ENVIRONMENT
================================================================================

You MUST create a virtual python environment specific for the version of Python
you are planning to use, for the following reasons:
    1. everything else that relies on the specifc Python version can properly 
    locate what it needs, without interference from the system's default Python
    interpreter
    2. Any Python packages installed specifically for the Python version using 
    the version-specifc 'pip' tool will not interfere (or worse, ovderwrite)
    system-wide packages

After installing Python (e.g., 3.9.7, see above) run from a (regular) command prompt:

pip install virtualenv

Then:

1) cd into a dfrive:\directory_path WITHOUT SPACES IN THE PATH NAME 

2) run virtualenv <your_preferred_environment_name> e.g.:
    
    virtualenv scipyen
    
3) Proceed to install the virtual python environment activation scripts

================================================================================
VIRTUAL PYTHON ENVIRONMENT ACTIVATION SCRIPTS:
================================================================================

1. Create a Scripts directory in your Windows home directory (%USERPROFILE%)

2. Add to your %PATH% PERMANENTLY:

	%USERPROFILE%\Scripts
	

(use Windows settings, search for "environment", select 
"Edit environment variables for your account" -> in the new dialog edit %PATH% ->
"add" %USERPROFILE%\Scripts)

* restart the command prompt

3. Copy scipyen_startup.py to <where your environment is>\Scripts

4. copy scipyact.bat, vs64.bat and scipyact_vs64.bat to %USERPROFILE%\Scripts

(NOTE: you can name these scripts whatever you like, just make note of what each
does; in the following, I will use the above names by convention)

4.1. Scripts usage:
    scipyact.bat => activates the virtual python environment <- USE THIS FOR REGULAR
        USE OF Scipyen, inside the virtual python environment
        
    vs64.bat => activates Visual Studio 2019 development environment <- use this
        for building software INDEPENDENT OF the virtual python environment
        
    scipyact_vs64.bat => activates BOTH <- use THIS for building Scipyen's
        dependencies INSIDE the virtual python environment (RECOMMENDED)
        
    



