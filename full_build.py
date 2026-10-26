"""
full_build.py - Script untuk build executable + installer secara otomatis
"""

import os
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output encoding if supported by terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_command(cmd, description):
    """Run command dan handle error"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False)
        if result.returncode != 0:
            print(f"[ERROR] {description} gagal")
            return False
        print(f"[OK] {description} berhasil")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    print("""
    +------------------------------------------------------------+
    |   A Latee Library - Full Build (Executable + Installer)   |
    +------------------------------------------------------------+
    """)
    
    # Check virtual environment
    venv_python = r".\.venv\Scripts\python.exe"
    if not os.path.exists(venv_python):
        print("[ERROR] Virtual environment tidak ditemukan")
        print("   Jalankan: python -m venv .venv")
        sys.exit(1)
    
    print("[OK] Virtual environment ditemukan")
    
    # Step 1: Build Executable
    print("\n[STEP 1] Building Executable...")
    cmd_exe = f'"{venv_python}" -m PyInstaller LibraryApp.spec --clean'
    if not run_command(cmd_exe, "Build Executable"):
        sys.exit(1)
    
    # Check executable
    if not os.path.exists("dist/A Latee Library.exe"):
        print("[ERROR] Executable tidak ditemukan di dist/")
        sys.exit(1)
    
    print("[OK] Executable dibuat: dist/A Latee Library.exe")
    
    # Step 2: Check NSIS
    print("\n[STEP 2] Checking NSIS...")
    nsis_cmd = "makensis.exe"
    nsis_found = False
    result = subprocess.run(f"{nsis_cmd} /?", shell=True, capture_output=True)
    if result.returncode == 0:
        nsis_found = True
    else:
        for standard_path in [r"C:\Program Files (x86)\NSIS\makensis.exe", r"C:\Program Files\NSIS\makensis.exe"]:
            if os.path.exists(standard_path):
                nsis_cmd = f'"{standard_path}"'
                nsis_found = True
                break

    if not nsis_found:
        print("[ERROR] NSIS tidak terinstall atau tidak di PATH")
        print("\nSolusi:")
        print("1. Download NSIS: https://nsis.sourceforge.io/Download")
        print("2. Install NSIS dengan 'Add to PATH'")
        print("3. Restart PowerShell")
        print("4. Jalankan script ini lagi")
        sys.exit(1)
    
    print(f"[OK] NSIS ditemukan: {nsis_cmd}")
    
    # Step 3: Build Installer
    print("\n[STEP 3] Building Installer...")
    cmd_nsis = f"{nsis_cmd} installer.nsi"
    if not run_command(cmd_nsis, "Build Installer"):
        sys.exit(1)
    
    # Check installer
    if not os.path.exists("Latee_Library_Installer_v1.0.exe"):
        print("[ERROR] Installer tidak ditemukan")
        sys.exit(1)
    
    print("[OK] Installer dibuat: Latee_Library_Installer_v1.0.exe")
    
    # Success
    print(f"\n{'='*60}")
    print("  [OK] BUILD BERHASIL!")
    print(f"{'='*60}")
    print("\nFile Output:")
    print("   1. dist/A Latee Library.exe (portable executable)")
    print("   2. Latee_Library_Installer_v1.0.exe (installer NSIS)")
    print("\nLangkah berikutnya:")
    print("   1. Test installer: .\\Latee_Library_Installer_v1.0.exe")
    print("   2. Distribute ke user")
    print("\nSelesai!")

if __name__ == "__main__":
    main()
