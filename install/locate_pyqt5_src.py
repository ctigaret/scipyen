# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

from distlib.locators import locate
pyqt5_locator = locate("PyQt5")
pyqt5_src_url = pyqt5_locator.download_url
print(pyqt5_src_url)
