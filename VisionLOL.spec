# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para VisionLOL
Gera um único executável Windows sem precisar de Python instalado.

Uso local:
    pip install pyinstaller
    pyinstaller VisionLOL.spec
"""

import os
import sys
from pathlib import Path

# ── Haar cascades do OpenCV (necessários para detecção facial) ──────────────
import cv2
_cv2_data = os.path.join(os.path.dirname(cv2.__file__), "data")

block_cipher = None

a = Analysis(
    ["gui_app_integrated.py"],
    pathex=[],
    binaries=[],
    datas=[
        (_cv2_data,            "cv2/data"),
        ("config.example.json", "."),
    ],
    hiddenimports=[
        # Pillow
        "PIL._tkinter_finder",
        # pynput — backends Win32
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        # Módulos riot_api (PyInstaller pode não detectar imports dinâmicos)
        "riot_api.config",
        "riot_api.riot_http",
        "riot_api.match_api",
        "riot_api.live_client",
        "riot_api.map_visualizer",
        "riot_api.team_viewer",
        "riot_api.performance_radar",
        "riot_api.dashboard_viewer",
        "riot_api.replay_viewer",
        "riot_api.replay_engine",
        "riot_api.scrim_dashboard",
        "riot_api.pathing_visualizer",
        "riot_api.proximity_tracker",
        "riot_api.reaction_analyzer",
        "riot_api.data_correlator",
        "riot_api.scrim_server",
        # Flask (servidor de scrims embutido)
        "flask",
        "flask.json",
        "werkzeug",
        "werkzeug.serving",
        "werkzeug.wrappers",
        "blinker",
        "jinja2",
        "itsdangerous",
        "click",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclui pacotes pesados desnecessários para reduzir tamanho do .exe
    excludes=["matplotlib", "scipy", "pandas", "IPython", "jupyter",
              "notebook", "PyQt5", "PyQt6", "wx"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="VisionLOL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # sem janela de console (GUI puro)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
