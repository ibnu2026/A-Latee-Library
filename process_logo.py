#!/usr/bin/env python3
"""
Process LOGO.jpg:
1. Make background transparent outside the triangle
2. Save as PNG with transparency
3. Convert to ICO format for app icon
"""

from PIL import Image, ImageDraw
import os

# File paths
assets_dir = os.path.join(os.path.dirname(__file__), "assets")
logo_jpg = os.path.join(assets_dir, "LOGO.jpg")
logo_png = os.path.join(assets_dir, "LOGO.png")
logo_ico = os.path.join(assets_dir, "app_icon.ico")

print(f"Processing LOGO from: {logo_jpg}")

# Open the original image
img = Image.open(logo_jpg)
print(f"Original image size: {img.size}")

# Convert to RGBA for transparency
img_rgba = img.convert("RGBA")
width, height = img_rgba.size

# Create a mask to make background transparent outside triangle
# Assuming triangle shape is defined by detecting the colored area
# We'll use a color-based approach to identify the triangle

pixels = img_rgba.load()
data = img_rgba.getdata()

# Convert to RGBA list for manipulation
new_data = []
for item in data:
    # If pixel is close to white (background), make it transparent
    # White is (255, 255, 255), but allow some tolerance for compression artifacts
    r, g, b = item[:3]
    
    # Check if pixel is close to white
    if r > 240 and g > 240 and b > 240:
        # Make it fully transparent
        new_data.append((r, g, b, 0))
    else:
        # Keep the pixel with full opacity
        new_data.append((r, g, b, 255))

img_rgba.putdata(new_data)

# Save as PNG with transparency
img_rgba.save(logo_png, "PNG")
print(f"✓ Saved transparent PNG: {logo_png}")

# Convert to ICO format (multiple sizes for better quality)
# Create ICO with standard sizes
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_images = []

for size in sizes:
    ico_img = img_rgba.resize(size, Image.Resampling.LANCZOS)
    ico_images.append(ico_img)

# Save as ICO
img_rgba.save(logo_ico, "ICO", sizes=sizes)
print(f"✓ Saved ICO icon: {logo_ico}")

print("\n✓ LOGO processing complete!")
print(f"  - PNG (transparent): {logo_png}")
print(f"  - ICO (app icon): {logo_ico}")
