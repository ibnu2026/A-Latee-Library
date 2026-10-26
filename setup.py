"""
setup.py - Script untuk membuat installer .MSI menggunakan py2exe
Install: pip install py2exe
"""

from distutils.core import setup
import py2exe
import os

# Konfigurasi untuk installer
setup(
    name="@ Latee Library",
    version="1.0.0",
    description="Aplikasi Manajemen Perpustakaan Digital",
    author="Ahmad Ibnu Zaini",
    
    windows=[{
        "script": "LibraryDekstopApp.py",
        "icon_resources": [(1, "assets/LOGO_transparent.ico")],
    }],
    
    options={
        "py2exe": {
            "dist_dir": "installer",
            "bundle_files": 3,  # Bundel semua DLL
            "includes": [
                "PyQt5",
                "cv2",
                "PIL",
                "pyzbar",
                "matplotlib",
                "pandas",
                "openpyxl",
                "reportlab",
            ],
        }
    },
    
    data_files=[
        ("assets", [
            "assets/LOGO_transparent.ico",
            # Tambahkan assets lain jika ada
        ]),
    ],
)
