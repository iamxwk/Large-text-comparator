# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

main_script = 'large_text_comparator.py'

icon_file = 'app_icon.icns'

a = Analysis(
    [main_script],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt5.sip', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LargeTextComparator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    icon=icon_file,
    console=False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LargeTextComparator'
)

app = BUNDLE(
    coll,
    name='LargeTextComparator.app',
    icon=icon_file,
    bundle_identifier='com.xwk.large_text_comparator',
    info_plist={
        'CFBundleName': 'LargeTextComparator',
        'CFBundleDisplayName': 'LargeTextComparator',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'NSPrincipalClass': 'NSApplication'
    }
)
