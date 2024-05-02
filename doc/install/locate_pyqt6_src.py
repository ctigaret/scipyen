from distlib.locators import locate
pyqt6_locator = locate("PyQt6")
pyqt6_src_url = pyqt6_locator.download_url
print(pyqt6_src_url)
