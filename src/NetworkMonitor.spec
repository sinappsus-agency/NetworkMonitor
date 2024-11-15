# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Set the environment variables
os.environ['TCL_LIBRARY'] = r'C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

# Collect Tcl/Tk data files
tcl_data_files = collect_data_files('tcl', subdir='tcl8.6')
tk_data_files = collect_data_files('tk', subdir='tk8.6')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=tcl_data_files + tk_data_files,
    datas=[
        ('C:\\Users\\artgr\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6', 'tcl8.6'),
        ('C:\\Users\\artgr\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6', 'tk8.6')
    ],
    hiddenimports=['requests', 'urllib3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='NetworkMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True
)