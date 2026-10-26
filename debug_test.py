#!/usr/bin/env python3
"""
Test script untuk debug error "too many values to unpack"
"""

import sys
import traceback

try:
    print("Step 1: Import LibraryDekstopApp...")
    from LibraryDekstopApp import Database, MainWindow, AuthWindow
    print("✓ Import berhasil")
    
    print("\nStep 2: Membuat Database...")
    db = Database()
    print("✓ Database berhasil dibuat")
    
    print("\nStep 3: Testing list_users()...")
    users = db.list_users()
    print(f"✓ list_users() berhasil: {len(users)} users")
    if users:
        print(f"  First user: {users[0]}")
    
    print("\nStep 4: Testing authenticate_user()...")
    user = db.authenticate_user("ibnu2026", "123456")  # Ganti dengan password yang benar
    print(f"Result: {user}")
    
    print("\nStep 5: Testing MainWindow init...")
    print("Note: Ini akan gagal karena Qt App belum ada, tapi kita bisa lihat errornya")
    try:
        main = MainWindow(db=db)
        print("✓ MainWindow berhasil dibuat")
    except Exception as e:
        print(f"❌ MainWindow error: {e}")
        traceback.print_exc()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ Debug test selesai")
print("="*60)
