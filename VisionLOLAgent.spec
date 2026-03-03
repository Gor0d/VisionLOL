# -*- mode: python ; coding: utf-8 -*-
"""
VisionLOLAgent.spec — PyInstaller spec para o agente do jogador.

Build:
    pyinstaller VisionLOLAgent.spec

Output: dist/VisionLOLAgent.exe
"""

a = Analysis(
    ["agent/agent_main.py"],
    pathex=["agent"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "agent_config",
        "urllib3",
        "urllib3.util",
        "urllib3.util.retry",
        "requests",
        "requests.adapters",
        "certifi",
        "charset_normalizer",
        "idna",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "scipy", "pandas", "numpy",
        "IPython", "jupyter", "PIL", "cv2",
        "flask", "werkzeug", "jinja2",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VisionLOLAgent",
    debug=False,
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
    icon=None,
)
