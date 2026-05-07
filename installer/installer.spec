# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for WinLLM_Setup.exe
Bundles the installer GUI + all frontend/server assets.
"""
import os
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'installer' / 'installer.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'frontend'),  'frontend'),
        (str(ROOT / 'server'),    'server'),
        (str(ROOT / 'config'),    'config'),
    ],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
        'winreg', 'ctypes', 'ctypes.wintypes',
        'urllib.request', 'urllib.error',
        'threading', 'subprocess', 'zipfile', 'tarfile', 'tempfile',
        'json', 'shutil', 'pathlib', 'time', 'os', 'sys',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'pandas', 'matplotlib', 'PIL', 'cv2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WinLLM_Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,       # request admin on launch
    icon=None,
    version_file=None,
    onefile=True,
)
