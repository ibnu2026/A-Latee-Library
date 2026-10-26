#!/usr/bin/env python3
"""
Analyze the design image to find the color of "berlaku sampai 3 tahun" text
"""

from PIL import Image
import os

design_path = os.path.join(os.getcwd(), "assets", "depan.jpg")

if not os.path.exists(design_path):
    print(f"❌ Design file not found: {design_path}")
    exit(1)

# Open design image
design_img = Image.open(design_path)
print(f"✓ Design image opened: {design_img.size}")

# Sample some pixel colors from the design
# The text "berlaku sampai 3 tahun" appears to be in the middle-right area
# Let's sample a few locations

# Extract RGB from various points to find text color
pixels = design_img.load()

# Sample points (you can adjust these)
sample_points = [
    (630, 400),  # Right side, middle-lower area
    (650, 420),  # Right side, middle-lower area
    (670, 410),  # Right side, middle-lower area
    (700, 395),  # Far right
    (720, 405),  # Far right, lower
]

print("\n📍 Sampling pixel colors from design image:")
print("-" * 50)

colors_found = {}
for x, y in sample_points:
    try:
        pixel = pixels[x, y]
        # Handle both RGB and RGBA
        if len(pixel) == 4:
            r, g, b, a = pixel
        else:
            r, g, b = pixel
        
        color_key = (r, g, b)
        if color_key not in colors_found:
            colors_found[color_key] = []
        colors_found[color_key].append((x, y))
        
        print(f"Point ({x}, {y}): RGB({r}, {g}, {b})")
    except Exception as e:
        print(f"⚠️  Error sampling ({x}, {y}): {e}")

print("\n📊 Unique colors found:")
print("-" * 50)
for color, points in sorted(colors_found.items(), key=lambda x: len(x[1]), reverse=True):
    r, g, b = color
    print(f"RGB({r:3d}, {g:3d}, {b:3d}): Found at {len(points)} point(s)")

print("\n💡 Most likely text color (appears most frequently):")
if colors_found:
    most_common = max(colors_found.items(), key=lambda x: len(x[1]))
    color = most_common[0]
    print(f"   RGB{color}")
