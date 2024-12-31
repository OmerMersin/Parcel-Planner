# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['parcel_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('map.html', 'map.html'),
        ('map_tiles/no_tile_found.png','no_tile_found.png'),
        ('web_resources', 'web_resources'),
        ('translated_es.qm', '.'),
        ('DRONETOOLS.ico', '.'),
        ('splash4.png', '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

splash = Splash('splash5.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(10, 50),
                text_size=8,
                text_color='black')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,                   # <-- both, splash target
    splash.binaries,          # <-- and splash binaries
    [],
    name='Parcel Planner',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="C:\\Users\\Getac\\Documents\\Omer Mersin\\codes\\parcel_planner\\parceland\\DRONETOOLS.ico",
    onefile=True,
)
