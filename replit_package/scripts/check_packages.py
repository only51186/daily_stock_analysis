#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check installed packages
"""

import sys

sources = ['openbb', 'akshare', 'baostock', 'adata', 'pyqlib', 'vnpy', 'hikyuu']

for s in sources:
    try:
        __import__(s)
        print(f'{s}: OK')
    except ImportError:
        print(f'{s}: NOT INSTALLED')
