#!/usr/bin/env python3
"""
Card Position Configuration Tool
Tool untuk menentukan posisi QR code pada desain kartu secara visual
"""
import os
import json
from PIL import Image, ImageDraw

def find_design_file(filename="depan.jpg"):
    """Cari file desain di berbagai lokasi"""
    paths = [
        os.path.join("assets", filename),
        os.path.join(os.path.dirname(__file__), "assets", filename),
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def create_position_preview(design_path, x, y, size, align="center"):
    """
    Buat preview desain dengan marker untuk posisi QR code
    
    Parameters:
    - design_path: path ke file desain
    - x: posisi x (0-1 = relative, >1 = pixel)
    - y: posisi y (0-1 = relative, >1 = pixel)
    - size: ukuran QR (0-1 = relative to width, >1 = pixel)
    - align: alignment (center, top-left, top-right, bottom-left, bottom-right)
    """
    
    img = Image.open(design_path)
    width, height = img.size
    
    # Hitung ukuran
    if isinstance(size, float) and size <= 1:
        qr_size = int(width * size)
    else:
        qr_size = int(size)
    
    # Hitung posisi X
    if isinstance(x, float) and x <= 1:
        pos_x = int(width * x)
    else:
        pos_x = int(x)
    
    # Hitung posisi Y
    if isinstance(y, float) and y <= 1:
        pos_y = int(height * y)
    else:
        pos_y = int(y)
    
    # Adjust berdasarkan alignment
    if align == "center":
        pos_x -= qr_size // 2
        pos_y -= qr_size // 2
    elif align == "top-right":
        pos_x -= qr_size
    elif align == "bottom-left":
        pos_y -= qr_size
    elif align == "bottom-right":
        pos_x -= qr_size
        pos_y -= qr_size
    
    # Copy untuk edit
    preview = img.copy()
    draw = ImageDraw.Draw(preview)
    
    # Draw rectangle untuk QR position
    rect_coords = [
        (pos_x, pos_y),
        (pos_x + qr_size, pos_y + qr_size)
    ]
    draw.rectangle(rect_coords, outline=(255, 0, 0), width=3)
    draw.rectangle(rect_coords, outline=(0, 255, 0), width=1)
    
    # Draw center point
    center_x = pos_x + qr_size // 2
    center_y = pos_y + qr_size // 2
    draw.ellipse(
        [(center_x-5, center_y-5), (center_x+5, center_y+5)],
        fill=(255, 0, 0)
    )
    
    # Save preview
    preview_path = "card_position_preview.jpg"
    preview.save(preview_path, quality=95)
    
    return preview_path, (pos_x, pos_y, qr_size)

def show_config_guide():
    """Tampilkan panduan konfigurasi"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         CARD POSITION CONFIGURATION TOOL                       ║
╚════════════════════════════════════════════════════════════════╝

📋 Format card_config.json:
{
  "depan.jpg": {
    "qr_position": {
      "x": 0.75,           # Posisi X (0-1 = relatif, >1 = pixel)
      "y": 0.6,            # Posisi Y (0-1 = relatif, >1 = pixel)
      "size_percent": 0.25,# Ukuran QR (0-1 = % dari width, >1 = pixel)
      "align": "center"    # Alignment: center, top-left, top-right, bottom-left, bottom-right
    }
  }
}

📐 Koordinat Sistem:
  - (0, 0) = Top-left corner
  - (1, 1) = Bottom-right corner
  - (0.5, 0.5) = Center

🎯 Contoh Posisi Populer:

1. Bottom-Right Corner (Default):
   "x": 0.9, "y": 0.85, "size_percent": 0.2, "align": "top-left"

2. Center:
   "x": 0.5, "y": 0.5, "size_percent": 0.25, "align": "center"

3. Top-Right Corner:
   "x": 0.9, "y": 0.1, "size_percent": 0.2, "align": "top-right"

4. Bottom-Center:
   "x": 0.5, "y": 0.85, "size_percent": 0.2, "align": "center"

5. Custom (Pixel-based):
   "x": 100, "y": 50, "size_percent": 300, "align": "top-left"

🔍 CARA MENGGUNAKAN:
  1. Edit card_config.json dengan posisi yang Anda inginkan
  2. Jalankan script ini: python card_position_tool.py
  3. Preview akan disimpan sebagai card_position_preview.jpg
  4. Merah = border, Hijau = inner, Merah dot = center
  5. Sesuaikan nilai x, y, size sampai posisi pas
  6. Generate QR untuk member untuk melihat hasil final

    """)

def main():
    print("=" * 64)
    print("  CARD POSITION CONFIGURATION PREVIEW GENERATOR")
    print("=" * 64)
    
    show_config_guide()
    
    # Load config
    if not os.path.exists("card_config.json"):
        print("❌ card_config.json tidak ditemukan!")
        print("   Pastikan file ada di folder yang sama dengan script ini")
        return
    
    with open("card_config.json", "r") as f:
        config = json.load(f)
    
    # Find design file
    design_path = find_design_file("depan.jpg")
    if not design_path:
        print("❌ Desain (depan.jpg) tidak ditemukan!")
        return
    
    print(f"\n✓ Desain ditemukan: {design_path}")
    
    # Get config for depan.jpg
    design_config = config.get("depan.jpg", {})
    qr_config = design_config.get("qr_position", {})
    
    if not qr_config:
        print("❌ Konfigurasi QR position tidak ditemukan untuk depan.jpg!")
        return
    
    x = qr_config.get("x", 0.75)
    y = qr_config.get("y", 0.6)
    size = qr_config.get("size_percent", 0.25)
    align = qr_config.get("align", "center")
    
    print(f"\n📍 Konfigurasi saat ini:")
    print(f"   X: {x}")
    print(f"   Y: {y}")
    print(f"   Size: {size}")
    print(f"   Align: {align}")
    
    # Create preview
    print(f"\n🎨 Membuat preview...")
    preview_path, (pos_x, pos_y, qr_size) = create_position_preview(
        design_path, x, y, size, align
    )
    
    print(f"✅ Preview dibuat: {preview_path}")
    print(f"\n📐 Posisi final:")
    print(f"   X: {pos_x}px")
    print(f"   Y: {pos_y}px")
    print(f"   Size: {qr_size}x{qr_size}px")
    
    img = Image.open(design_path)
    print(f"\n📏 Desain ukuran: {img.width}x{img.height}px")
    
    print(f"""
✓ Preview sudah dibuat!
  Buka 'card_position_preview.jpg' untuk melihat posisi QR code.
  
📝 Jika ingin mengubah posisi:
  1. Edit nilai x, y, size_percent, align di card_config.json
  2. Jalankan script ini lagi untuk preview baru
  3. Ulangi sampai posisi sesuai
  4. Selamat! Posisi sudah optimal 🎉
    """)

if __name__ == "__main__":
    main()
