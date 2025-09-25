# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None


def get_project_root():
    return Path(__file__).resolve().parents[1]


a = Analysis([
    str(get_project_root() / "src" / "option_flow" / "desktop" / "app.py")
],
             pathex=[str(get_project_root())],
             binaries=[],
             datas=[],
             hiddenimports=["option_flow.launcher.runner", "option_flow.ingest.worker"],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='option-flow-desktop',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          argv_emulation=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='option-flow-desktop')
