realscript=`realpath $0`

echo "$realscript"

scipyendir=`dirname "$realscript"`

echo "$scipyendir"

env_name="scipyenv"

mamba activate "$env_name"

if test $? -ne 0  ; then
echo "Could not activate the mamba environment $env_name. Goodbye!"
exit 1
else
echo "The mamba environment $env_name activated"
fi

cd "$scipyendir"/src/scipyen/gui/scipyen_console_styles

if test $? -ne 0 ; then
echo "Trouble looking for "$scipyendir"/src/scipyen/gui/scipyen_console_styles. Goodbye!"
exit 1
else echo -e "Installing PyPi packages..."
fi

pip install .
pip install pyabf imreg-dft modelspec pyqtdarktheme

# (mamba create -y --name "$env_name" python=3.11 --file mamba_reqs.txt) && (mamba activate "$env_name" && cd $"scipyendir"/src/scipyen/gui/scipyen_console_styles && pip install . pyabf imreg-dft modelspec pyqtdarktheme)


