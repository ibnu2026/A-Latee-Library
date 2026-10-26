#!/usr/bin/env python3
"""
Test script untuk debug pembuatan kartu
"""
import os
import sys
from PIL import Image

def test_card_creation_debug():
    print("=" * 70)
    print("  DEBUG: TEST PEMBUATAN KARTU")
    print("=" * 70)
    
    # Simulasi parameter
    nama = "Test Anggota"
    nis = "bcbd51a1-97c"
    kamar = "A101"
    qr_path = "qrcodes/bcbd51a1-97c.png"
    
    print(f"\n📋 Parameter:")
    print(f"   Nama: {nama}")
    print(f"   NIS: {nis}")
    print(f"   Kamar: {kamar}")
    print(f"   QR Path: {qr_path}")
    
    # Setup folders
    cards_dir = "cards"
    os.makedirs(cards_dir, exist_ok=True)
    print(f"\n📁 Folder cards: {cards_dir}")
    print(f"   Exists: {os.path.exists(cards_dir)}")
    
    # Check design
    print(f"\n🎨 Cek desain kartu:")
    design_paths = [
        "assets/depan.jpg",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "depan.jpg"),
    ]
    
    design_path = None
    for path in design_paths:
        exists = os.path.exists(path)
        print(f"   {path}: {exists}")
        if exists:
            design_path = path
            break
    
    if not design_path:
        print(f"❌ Desain tidak ditemukan!")
        return False
    
    # Open design
    print(f"\n📖 Open desain: {design_path}")
    try:
        design_img = Image.open(design_path)
        design_width, design_height = design_img.size
        print(f"   ✓ Desain dibuka: {design_width}x{design_height}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Check QR
    print(f"\n📱 Cek QR code:")
    if not os.path.exists(qr_path):
        print(f"   ❌ QR tidak ditemukan: {qr_path}")
        return False
    
    print(f"   ✓ QR ditemukan: {qr_path}")
    
    # Open QR
    print(f"\n📖 Open QR code:")
    try:
        qr_img = Image.open(qr_path).convert("RGBA")
        print(f"   ✓ QR dibuka: {qr_img.size}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Resize QR (using simple default position for test)
    print(f"\n↔️ Resize QR code:")
    qr_size = int(design_width * 0.25)
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    print(f"   ✓ QR di-resize ke: {qr_size}x{qr_size}")
    
    # Paste
    print(f"\n🔧 Paste QR ke desain:")
    paste_x = int(design_width * 0.32) - qr_size // 2
    paste_y = int(design_height * 0.35) - qr_size // 2
    print(f"   Posisi: ({paste_x}, {paste_y})")
    
    try:
        if qr_img.mode == "RGBA":
            design_img.paste(qr_img, (paste_x, paste_y), qr_img)
        else:
            design_img.paste(qr_img, (paste_x, paste_y))
        print(f"   ✓ QR di-paste")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Save
    print(f"\n💾 Save kartu:")
    safe_nama = "".join(c for c in nama if c.isalnum() or c in (' ', '-', '_')).rstrip()
    card_filename = os.path.join(cards_dir, f"{safe_nama}_{nis}.jpg")
    print(f"   Path: {card_filename}")
    
    try:
        design_img.save(card_filename, quality=95)
        print(f"   ✓ Kartu disimpan")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify
    print(f"\n✅ Verify:")
    if os.path.exists(card_filename):
        size = os.path.getsize(card_filename) / 1024
        print(f"   ✓ File ada: {size:.1f} KB")
        print(f"\n✅ TEST PASSED!")
        return True
    else:
        print(f"   ❌ File tidak ditemukan setelah save")
        return False

if __name__ == "__main__":
    test_card_creation_debug()
