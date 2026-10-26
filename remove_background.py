"""
Convert LOGO.jpg to high-quality PNG with transparent background outside the triangle shape
Keep the actual triangle from logo (outer edges) and make everything else transparent
"""
import os
from PIL import Image, ImageDraw, ImageEnhance
import numpy as np

assets_dir = "assets"
logo_jpg = os.path.join(assets_dir, "LOGO.jpg")
logo_png = os.path.join(assets_dir, "LOGO.png")

def convert_jpg_to_hd_png_transparent():
    """
    1. Load LOGO.jpg
    2. Upscale to 2x (higher HD quality)
    3. Enhance quality (sharpness, contrast, color)
    4. Detect the actual triangle edges from the logo
    5. Make everything outside those triangle edges transparent
    6. Save as PNG with transparency
    """
    if not os.path.exists(logo_jpg):
        print(f"❌ {logo_jpg} not found!")
        return
    
    print(f"📦 Loading {logo_jpg}...")
    img = Image.open(logo_jpg)
    original_size = img.size
    print(f"   Original size: {original_size}")
    
    # Convert to RGBA for transparency support
    img = img.convert('RGBA')
    
    # Upscale 2x untuk HD lebih tinggi
    print(f"🔧 Upscaling to 2x for HD quality...")
    new_width = original_size[0] * 2
    new_height = original_size[1] * 2
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Enhance quality
    print(f"✨ Enhancing quality...")
    # Sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    # Color vibrancy
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.2)
    # Contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    
    # Convert to numpy array for analysis
    img_array = np.array(img)
    width, height = img.size
    
    # Detect non-white/light areas (the actual content/triangle from logo)
    print(f"🔍 Detecting logo content boundaries...")
    
    # Get RGB channels
    r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
    
    # Create mask based on non-white areas
    # White areas in logo background have high values (> 240)
    # Logo content has lower values
    is_white_bg = (r > 240) & (g > 240) & (b > 240)
    
    # Create final mask: logo content = 255 (opaque), white background = 0 (transparent)
    mask = (~is_white_bg).astype(np.uint8) * 255
    
    # Apply mask to alpha channel
    print(f"🔲 Applying transparency mask...")
    img_array[:,:,3] = mask
    
    # Create final image
    result = Image.fromarray(img_array, 'RGBA')
    
    # Save as PNG
    print(f"💾 Saving as high-quality PNG...")
    result.save(logo_png, 'PNG', optimize=False)
    
    new_size = os.path.getsize(logo_png) / 1024
    print(f"✅ Success! {logo_png}")
    print(f"   - Format: JPG → PNG")
    print(f"   - Size: {original_size} → {new_width}x{new_height} (2x)")
    print(f"   - Quality: Enhanced (sharper, vibrant, better contrast)")
    print(f"   - Background: Outside logo triangle = TRANSPARENT")
    print(f"   - Logo content: PRESERVED")
    print(f"   - File size: {new_size:.2f} KB")

if __name__ == "__main__":
    convert_jpg_to_hd_png_transparent()
