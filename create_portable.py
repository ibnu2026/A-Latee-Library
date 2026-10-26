#!/usr/bin/env python3
"""
create_portable.py - Create portable installer (ZIP format)
Compressed executable untuk distribusi mudah
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_portable_zip():
    """Create portable ZIP installer"""
    print("=" * 60)
    print("  A Latee Library - Portable Installer Creator")
    print("=" * 60)
    
    # Check executable exists
    exe_path = "dist/A Latee Library.exe"
    if not os.path.exists(exe_path):
        print("❌ Error: Executable tidak ditemukan")
        print("   Jalankan: python full_build.py")
        return False
    
    print(f"✓ Executable ditemukan: {exe_path}")
    print(f"  Ukuran: {os.path.getsize(exe_path) / (1024**2):.2f} MB")
    
    # Create installer folder
    installer_dir = "portable_installer"
    if os.path.exists(installer_dir):
        shutil.rmtree(installer_dir)
    os.makedirs(installer_dir)
    
    # Copy executable
    print("\n📋 Menyiapkan file...")
    shutil.copy(exe_path, os.path.join(installer_dir, "A Latee Library.exe"))
    print("  ✓ Executable disalin")
    
    # Create README
    readme_content = """
╔════════════════════════════════════════════════════════════╗
║          A LATEE LIBRARY - APLIKASI PERPUSTAKAAN          ║
╚════════════════════════════════════════════════════════════╝

PANDUAN INSTALASI CEPAT
═══════════════════════

1. EKSTRAK FILE
   - Ekstrak folder ini ke lokasi yang diinginkan
   - Contoh: C:\\Program Files\\Latee Library

2. JALANKAN APLIKASI
   - Buka folder dan double-click: A Latee Library.exe
   - Aplikasi akan berjalan langsung (portable - tidak perlu instalasi)

3. PERTAMA KALI JALANKAN
   - Aplikasi akan membuat database otomatis di:
     Windows: %APPDATA%\\Latee Library\\library_data.db
   - Data akan tersimpan dan persisten di folder tersebut

PERSYARATAN SISTEM
═══════════════════
- Windows 7 atau lebih baru (32-bit atau 64-bit)
- RAM minimal 2 GB
- Disk space: minimal 200 MB (untuk executable + database)

FITUR UTAMA
════════════
✓ Manajemen Buku (Tambah, Edit, Hapus, Cari)
✓ Manajemen Anggota/Pengunjung
✓ Pencatatan Peminjaman & Pengembalian
✓ Barcode & QR Code Scanning
✓ Fingerprint Recognition (Deli ES151)
✓ Laporan & Statistik
✓ Export ke Excel
✓ Multi-User dengan Authentication

TROUBLESHOOTING
════════════════

Q: Aplikasi tidak mau membuka?
A: Pastikan sudah install .NET Framework dan Visual C++ Redistributable

Q: Barcode scanner tidak berfungsi?
A: Install driver scanner barcode Anda terlebih dahulu

Q: Fingerprint machine tidak terdeteksi?
A: Check COM port di Device Manager dan pastikan baud rate 115200

BANTUAN & SUPPORT
══════════════════
- Baca dokumentasi di folder Documentation
- Lihat video tutorial yang disertakan
- Hubungi administrator sistem

═══════════════════════════════════════════════════════════════

Dibuat: 2025-11-15
Versi: 1.0
Lisensi: Internal Use Only

═══════════════════════════════════════════════════════════════
"""
    
    with open(os.path.join(installer_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("  ✓ README.txt dibuat")
    
    # Create batch file for easy launch
    bat_content = """@echo off
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   A LATEE LIBRARY - Starting Application...               ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
start "" "A Latee Library.exe"
"""
    
    with open(os.path.join(installer_dir, "Run_Latee_Library.bat"), "w", encoding="utf-8") as f:
        f.write(bat_content)
    print("  ✓ Run_Latee_Library.bat dibuat")
    
    # Create ZIP file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"Latee_Library_Portable_v1.0_{timestamp}.zip"
    
    print(f"\n📦 Membuat ZIP file: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(installer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, '.')
                zipf.write(file_path, arcname)
                size_mb = os.path.getsize(file_path) / (1024**2)
                print(f"  ✓ {file} ({size_mb:.2f} MB)")
    
    zip_size_mb = os.path.getsize(zip_filename) / (1024**2)
    print(f"\n✓ ZIP file berhasil dibuat!")
    print(f"  Filename: {zip_filename}")
    print(f"  Ukuran: {zip_size_mb:.2f} MB")
    
    # Cleanup
    print(f"\n🧹 Membersihkan folder temporary...")
    shutil.rmtree(installer_dir)
    print(f"  ✓ Folder {installer_dir} dihapus")
    
    print("\n" + "=" * 60)
    print("✅ PORTABLE INSTALLER BERHASIL DIBUAT!")
    print("=" * 60)
    print("\n📥 Cara menggunakan:")
    print(f"   1. Download/transfer file: {zip_filename}")
    print("   2. Ekstrak di lokasi yang diinginkan")
    print("   3. Jalankan: A Latee Library.exe")
    print("\n" + "=" * 60)
    
    return True

if __name__ == "__main__":
    create_portable_zip()
