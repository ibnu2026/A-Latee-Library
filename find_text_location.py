#!/usr/bin/env python3
"""
Display design image to visual location of text
"""

from PIL import Image
import os

design_path = os.path.join(os.getcwd(), "assets", "depan.jpg")

if not os.path.exists(design_path):
    print(f"❌ Design file not found: {design_path}")
    exit(1)

# Open and display
design_img = Image.open(design_path)
print(f"✓ Design image size: {design_img.size} (width x height)")
print(f"   Width: {design_img.width}px")
print(f"   Height: {design_img.height}px")

# Show where some common areas are
print("\n📍 Key percentage points on image:")
print(f"   Center: ({design_img.width//2}, {design_img.height//2})")
print(f"   Right side (78%): ({int(design_img.width*0.78)}, {int(design_img.height*0.45)})")
print(f"   Bottom right (80%, 80%): ({int(design_img.width*0.80)}, {int(design_img.height*0.80)})")

# Let's sample more strategic points
# "berlaku sampai 3 tahun" is likely on white area at the bottom or right
pixels = design_img.load()

print("\n📍 Sampling across the bottom-right area (more likely text location):")
print("-" * 50)

# More bottom area
sample_points = [
    (650, 480),  # Bottom area
    (670, 490),  # Bottom area
    (690, 475),  # Bottom area  
    (710, 485),  # Bottom area
    (730, 495),  # Bottom area
    (400, 520),  # Lower middle
    (500, 530),  # Lower middle
    (600, 540),  # Lower right
]

for x, y in sample_points:
    try:
        pixel = pixels[x, y]
        if len(pixel) == 4:
            r, g, b, a = pixel
        else:
            r, g, b = pixel
        
        # Check if it's text (dark color)
        is_likely_text = (r < 150 and g < 150 and b < 150)
        marker = "← TEXT?" if is_likely_text else ""
        print(f"Point ({x:3d}, {y:3d}): RGB({r:3d}, {g:3d}, {b:3d}) {marker}")
    except Exception as e:
        print(f"⚠️  Error at ({x}, {y}): {e}")

print("\n💡 Note: If no dark colors found, the text might be:")
print("   - Very small to sample easily")
print("   - In a different location than expected")
print("   - White/light colored text on darker background")
