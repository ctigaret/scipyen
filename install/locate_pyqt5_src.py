from distlib.locators import locate
pyqt5_locator = locate("PyQt5")
pyqt5_src_url = pyqt5_locator.download_url
print(pyqt5_src_url)
