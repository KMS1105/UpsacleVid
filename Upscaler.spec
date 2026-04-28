# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

numpy_data = collect_all('numpy')
cv2_data = collect_all('cv2')
onnx_data = collect_all('onnxruntime')

a = Analysis(
    ['.exe\\Code\\Launch.py'],
    pathex=[],
    binaries=numpy_data[1] + cv2_data[1] + onnx_data[1],
    datas=[('.exe', '.exe')] + numpy_data[0] + cv2_data[0] + onnx_data[0],
    hiddenimports=['cv2', 'onnxruntime', 'sip', 'torch.distributed'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch.testing', 'expecttest', 'torch.ao',
        'sympy', 'networkx', 'numba', 'scipy', 'matplotlib', 'tkinter',
        'onnx.reference'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Upscaler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, #False
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Upscaler',
)