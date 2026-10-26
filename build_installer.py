"""
build_installer.py - Script untuk membantu membuat installer NSIS
"""

import os
import subprocess
import sys
from pathlib import Path

def check_nsis_installed():
    """Check apakah NSIS sudah terinstall"""
    nsis_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    
    for path in nsis_paths:
        if os.path.exists(path):
            return path
    
    return None

def build_installer():
    """Build installer NSIS"""
    print("=" * 60)
    print("  A Latee Library - Installer Builder")
    print("=" * 60)
    
    # Check executable exists
    if not os.path.exists("dist/A Latee Library.exe"):
        print("Error: dist/A Latee Library.exe tidak ditemukan")
        print("   Jalankan: python -m PyInstaller LibraryApp.spec --clean")
        sys.exit(1)
    
    print("[OK] Executable ditemukan: dist/A Latee Library.exe")
    
    # Check NSIS
    nsis_path = check_nsis_installed()
    if not nsis_path:
        print("\nError: NSIS belum terinstall!")
        print("\nSolusi:")
        print("1. Download NSIS dari: https://nsis.sourceforge.io/Download")
        print("2. Install NSIS (pilih opsi 'Add to PATH')")
        print("3. Jalankan script ini lagi")
        sys.exit(1)
    
    print(f"[OK] NSIS ditemukan: {nsis_path}")
    
    # Check NSI script
    if not os.path.exists("installer.nsi"):
        print("Error: installer.nsi tidak ditemukan")
        sys.exit(1)
    
    print("[OK] Script installer ditemukan: installer.nsi")
    
    # Build installer
    print("\nMembuat installer...")
    try:
        result = subprocess.run(
            [nsis_path, "installer.nsi"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("[OK] Installer berhasil dibuat!")
            print("\nLokasi file:")
            print("   Latee_Library_Installer_v1.0.exe")
            print("\nLangkah berikutnya:")
            print("   1. Test installer di virtual machine atau folder test")
            print("   2. Distribusikan ke pengguna")
            print("   3. Pengguna tinggal double-click untuk install")
        else:
            print(f"Error building installer:\n{result.stderr}")
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Timeout: Proses build terlalu lama")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_installer()
